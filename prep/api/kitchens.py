"""Kitchen management API endpoints with compliance integrations."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import Select, and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from prep.compliance.constants import BOOKING_COMPLIANCE_BANNER
from prep.database.connection import AsyncSessionLocal, get_db
from prep.models import Kitchen
from prep.notifications.regulatory import RegulatoryNotifier
from prep.notifications.service import NotificationService
from prep.regulatory.analyzer import RegulatoryAnalyzer
from prep.regulatory.service import get_regulations_for_jurisdiction
from prep.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kitchens", tags=["kitchens"])


class KitchenCreate(BaseModel):
    """Payload used to create a kitchen listing."""

    name: str
    address: str
    description: str
    pricing: dict[str, Any]
    equipment: List[str] = Field(default_factory=list)
    state: Optional[str] = None
    city: Optional[str] = None
    host_id: Optional[str] = None
    health_permit_number: Optional[str] = None
    last_inspection_date: Optional[datetime] = None
    insurance_info: Optional[dict[str, Any]] = None
    zoning_type: Optional[str] = None


class KitchenResponse(KitchenCreate):
    """Kitchen representation returned by the API."""

    id: str
    host_id: str
    compliance_status: Optional[str] = None
    risk_score: Optional[int] = None
    last_compliance_check: Optional[datetime] = None
    created_at: datetime


class KitchenComplianceResponse(BaseModel):
    """Structured response for compliance analysis."""

    kitchen_id: str
    compliance_level: str
    risk_score: int
    missing_requirements: List[str]
    recommendations: List[str]
    last_analyzed: str
    city: Optional[str] = None
    state: Optional[str] = None
    booking_restrictions_banner: Optional[str] = None


def _serialize_kitchen(kitchen: Kitchen) -> KitchenResponse:
    """Convert a Kitchen ORM instance into an API response."""

    return KitchenResponse(
        id=str(kitchen.id),
        host_id=str(kitchen.host_id),
        name=kitchen.name,
        address=kitchen.address,
        description=kitchen.description,
        pricing=kitchen.pricing or {},
        equipment=kitchen.equipment or [],
        state=kitchen.state,
        city=kitchen.city,
        compliance_status=kitchen.compliance_status,
        risk_score=kitchen.risk_score,
        last_compliance_check=kitchen.last_compliance_check,
        created_at=kitchen.created_at,
        health_permit_number=kitchen.health_permit_number,
        last_inspection_date=kitchen.last_inspection_date,
        insurance_info=kitchen.insurance_info,
        zoning_type=kitchen.zoning_type,
    )


@router.post("/", response_model=KitchenResponse, status_code=status.HTTP_201_CREATED)
async def create_kitchen(
    kitchen_data: KitchenCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> KitchenResponse:
    """Create a new kitchen listing and trigger compliance analysis."""

    try:
        host_id = uuid.UUID(kitchen_data.host_id) if kitchen_data.host_id else uuid.uuid4()
    except ValueError as exc:  # pragma: no cover - validation guard
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid host ID") from exc

    state_value = kitchen_data.state.upper() if kitchen_data.state else None
    city_value = kitchen_data.city.strip() if kitchen_data.city else None

    new_kitchen = Kitchen(
        name=kitchen_data.name,
        host_id=host_id,
        address=kitchen_data.address,
        description=kitchen_data.description,
        pricing=kitchen_data.pricing,
        equipment=kitchen_data.equipment,
        state=state_value,
        city=city_value,
        health_permit_number=kitchen_data.health_permit_number,
        last_inspection_date=kitchen_data.last_inspection_date,
        insurance_info=kitchen_data.insurance_info,
        zoning_type=kitchen_data.zoning_type,
    )

    db.add(new_kitchen)
    await db.commit()
    await db.refresh(new_kitchen)

    background_tasks.add_task(analyze_kitchen_compliance, str(new_kitchen.id))

    return _serialize_kitchen(new_kitchen)


@router.get("/{kitchen_id}", response_model=KitchenResponse)
async def get_kitchen(kitchen_id: str, db: AsyncSession = Depends(get_db)) -> KitchenResponse:
    """Retrieve a specific kitchen by its identifier."""

    kitchen = await _get_kitchen_or_404(db, kitchen_id)
    return _serialize_kitchen(kitchen)


@router.get("/", response_model=List[KitchenResponse])
async def list_kitchens(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> List[KitchenResponse]:
    """List kitchens with pagination support."""

    result = await db.execute(select(Kitchen).offset(skip).limit(limit))
    kitchens = result.scalars().all()
    return [_serialize_kitchen(kitchen) for kitchen in kitchens]


@router.get("/{kitchen_id}/compliance", response_model=KitchenComplianceResponse)
async def get_kitchen_compliance(
    kitchen_id: str,
    db: AsyncSession = Depends(get_db),
) -> KitchenComplianceResponse:
    """Get the compliance status for a kitchen."""

    kitchen = await _get_kitchen_or_404(db, kitchen_id)

    analyzer = RegulatoryAnalyzer()
    kitchen_payload = {
        "id": str(kitchen.id),
        "state": kitchen.state,
        "city": kitchen.city,
        "health_permit_number": kitchen.health_permit_number,
        "last_inspection_date": kitchen.last_inspection_date,
        "insurance": kitchen.insurance_info,
        "zoning_type": kitchen.zoning_type,
    }

    regulations = await get_regulations_for_jurisdiction(db, kitchen.state, kitchen.city)
    analysis = await analyzer.analyze_kitchen_compliance(kitchen_payload, regulations)

    settings = get_settings()
    banner = (
        BOOKING_COMPLIANCE_BANNER if settings.compliance_controls_enabled else None
    )

    return KitchenComplianceResponse(
        kitchen_id=str(kitchen.id),
        compliance_level=analysis.overall_compliance.value,
        risk_score=analysis.risk_score,
        missing_requirements=analysis.missing_requirements,
        recommendations=analysis.recommendations,
        last_analyzed=analysis.last_analyzed.isoformat(),
        city=kitchen.city,
        state=kitchen.state,
        booking_restrictions_banner=banner,
    )


@router.get("/search/compliant", response_model=List[KitchenResponse])
async def search_compliant_kitchens(
    state: str,
    city: Optional[str] = Query(default=None),
    min_compliance_level: str = Query("partial_compliance"),
    db: AsyncSession = Depends(get_db),
) -> List[KitchenResponse]:
    """Search for kitchens that meet a minimum compliance level."""

    allowed_levels = {"compliant", "partial_compliance", "non_compliant", "unknown"}
    if min_compliance_level not in allowed_levels:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid compliance level filter")

    state_filter = state.upper()
    filters = [func.upper(Kitchen.state) == state_filter]
    if city:
        filters.append(Kitchen.city == city)

    if min_compliance_level == "compliant":
        filters.append(Kitchen.compliance_status == "compliant")
    elif min_compliance_level == "partial_compliance":
        filters.append(Kitchen.compliance_status.in_(["compliant", "partial_compliance"]))
    elif min_compliance_level == "non_compliant":
        filters.append(Kitchen.compliance_status != "unknown")

    stmt: Select[Kitchen] = select(Kitchen).where(and_(*filters))
    stmt = stmt.order_by(
        case(
            (
                Kitchen.compliance_status == "compliant",
                3,
            ),
            (
                Kitchen.compliance_status == "partial_compliance",
                2,
            ),
            (
                Kitchen.compliance_status == "non_compliant",
                1,
            ),
            else_=0,
        ).desc(),
        Kitchen.created_at.desc(),
    )

    result = await db.execute(stmt)
    kitchens = result.scalars().all()
    return [_serialize_kitchen(kitchen) for kitchen in kitchens]


async def _get_kitchen_or_404(db: AsyncSession, kitchen_id: str) -> Kitchen:
    """Load a kitchen by identifier or raise a 404 error."""

    try:
        kitchen_uuid = uuid.UUID(kitchen_id)
    except ValueError as exc:  # pragma: no cover - validation guard
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid kitchen ID") from exc

    result = await db.execute(select(Kitchen).where(Kitchen.id == kitchen_uuid))
    kitchen = result.scalar_one_or_none()
    if kitchen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")
    return kitchen


async def analyze_kitchen_compliance(kitchen_id: str) -> None:
    """Background task that runs compliance analysis for a kitchen."""

    async with AsyncSessionLocal() as session:
        kitchen = await session.get(Kitchen, uuid.UUID(kitchen_id))
        if kitchen is None:
            logger.warning("Kitchen %s not found for compliance analysis", kitchen_id)
            return

        analyzer = RegulatoryAnalyzer()
        kitchen_payload = {
            "id": str(kitchen.id),
            "state": kitchen.state,
            "city": kitchen.city,
            "health_permit_number": kitchen.health_permit_number,
            "last_inspection_date": kitchen.last_inspection_date,
            "insurance": kitchen.insurance_info,
            "zoning_type": kitchen.zoning_type,
        }
        regulations = await get_regulations_for_jurisdiction(session, kitchen.state, kitchen.city)

        previous_status = kitchen.compliance_status or "unknown"
        analysis = await analyzer.analyze_kitchen_compliance(kitchen_payload, regulations)

        kitchen.compliance_status = analysis.overall_compliance.value
        kitchen.risk_score = analysis.risk_score
        kitchen.last_compliance_check = analysis.last_analyzed

        await session.commit()

        status_changed = analysis.overall_compliance.value != previous_status
        is_non_compliant = analysis.overall_compliance.value != "compliant"
        if status_changed or is_non_compliant:
            notifier = RegulatoryNotifier(NotificationService())
            await notifier.notify_compliance_change(
                str(kitchen.id),
                previous_status,
                analysis.overall_compliance.value,
                analysis.missing_requirements,
            )
*** End Patch
