"""Kitchen management API endpoints with compliance integrations."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import Select, and_, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from prep.auth import User, get_current_user
from prep.compliance.constants import BOOKING_COMPLIANCE_BANNER, BOOKING_PILOT_BANNER
from prep.database.connection import AsyncSessionLocal, get_db
from prep.models import Kitchen, SanitationLog, SubscriptionStatus
from prep.notifications.regulatory import RegulatoryNotifier
from prep.notifications.service import NotificationService
from prep.observability.metrics import DELIVERY_KITCHENS_GAUGE
from prep.pilot.utils import is_pilot_location
from prep.regulatory.analyzer import RegulatoryAnalyzer
from prep.regulatory.location import resolve_by_zip
from prep.regulatory.service import get_regulations_for_jurisdiction
from prep.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kitchens", tags=["kitchens"])


_ZIP_PATTERN = re.compile(r"\b\d{5}(?:-\d{4})?\b")


def _extract_zip_code(address: str | None) -> str | None:
    """Extract a postal code from a free-form address string."""

    if not address:
        return None
    match = _ZIP_PATTERN.search(address)
    if match:
        return match.group(0)
    return None


def _collect_location_context(kitchen: Kitchen) -> dict[str, str | None]:
    """Collect location-derived metadata used for pilot feature flags."""

    insurance_info = kitchen.insurance_info if isinstance(kitchen.insurance_info, dict) else {}
    county = None
    if insurance_info:
        county = insurance_info.get("county") or insurance_info.get("county_name")

    return {
        "zip_code": _extract_zip_code(kitchen.address),
        "county": county,
    }


class KitchenCreate(BaseModel):
    """Payload used to create a kitchen listing."""

    name: str
    address: str
    description: str
    pricing: dict[str, Any]
    equipment: list[str] = Field(default_factory=list)
    state: str | None = None
    city: str | None = None
    postal_code: str | None = None
    county: str | None = None
    health_permit_number: str | None = None
    last_inspection_date: datetime | None = None
    insurance_info: dict[str, Any] | None = None
    zoning_type: str | None = None
    delivery_only: bool = False
    permit_types: list[str] = Field(default_factory=list)


class KitchenResponse(KitchenCreate):
    """Kitchen representation returned by the API."""

    id: str
    host_id: str
    compliance_status: str | None = None
    risk_score: int | None = None
    last_compliance_check: datetime | None = None
    created_at: datetime


class KitchenComplianceResponse(BaseModel):
    """Structured response for compliance analysis."""

    kitchen_id: str
    compliance_level: str
    risk_score: int
    missing_requirements: list[str]
    recommendations: list[str]
    last_analyzed: str
    city: str | None = None
    state: str | None = None
    county: str | None = None
    postal_code: str | None = None
    booking_restrictions_banner: str | None = None
    delivery_only: bool = False
    permit_types: list[str] = Field(default_factory=list)
    last_sanitation_log: datetime | None = None
    subscription_status: str | None = None
    trial_ends_at: str | None = None
    is_pilot_user: bool = False
    pilot_mode: bool = False
    override_allowed: bool = False


class SanitationLogCreate(BaseModel):
    """Payload describing a sanitation inspection entry."""

    logged_at: datetime | None = None
    status: str = Field(default="passed", pattern="^[a-zA-Z_]+$")
    inspector_name: str | None = None
    notes: str | None = None
    follow_up_required: bool = False


class SanitationLogResponse(SanitationLogCreate):
    """Serialized sanitation log returned by the API."""

    id: str
    kitchen_id: str
    logged_at: datetime


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
        postal_code=kitchen.postal_code,
        county=kitchen.county,
        compliance_status=kitchen.compliance_status,
        risk_score=kitchen.risk_score,
        last_compliance_check=kitchen.last_compliance_check,
        created_at=kitchen.created_at,
        health_permit_number=kitchen.health_permit_number,
        last_inspection_date=kitchen.last_inspection_date,
        insurance_info=kitchen.insurance_info,
        zoning_type=kitchen.zoning_type,
        delivery_only=bool(kitchen.delivery_only),
        permit_types=kitchen.permit_types or [],
    )


def _serialize_sanitation_log(entry: SanitationLog) -> SanitationLogResponse:
    """Normalize a sanitation log ORM row into API representation."""

    return SanitationLogResponse(
        id=str(entry.id),
        kitchen_id=str(entry.kitchen_id),
        logged_at=entry.logged_at,
        status=entry.status,
        inspector_name=entry.inspector_name,
        notes=entry.notes,
        follow_up_required=entry.follow_up_required,
    )


async def _refresh_delivery_gauge(db: AsyncSession) -> None:
    """Update the Prometheus gauge tracking delivery-only kitchens."""

    total = await db.scalar(select(func.count()).where(Kitchen.delivery_only.is_(True)))
    DELIVERY_KITCHENS_GAUGE.set(total or 0)


@router.post("/", response_model=KitchenResponse, status_code=status.HTTP_201_CREATED)
async def create_kitchen(
    kitchen_data: KitchenCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> KitchenResponse:
    """Create a new kitchen listing and trigger compliance analysis."""

    try:
        host_id = uuid.UUID(current_user.id)
    except ValueError as exc:  # pragma: no cover - validation guard
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid host ID"
        ) from exc

    state_value = kitchen_data.state.upper() if kitchen_data.state else None
    city_value = kitchen_data.city.strip() if kitchen_data.city else None
    postal_code_value = kitchen_data.postal_code.strip() if kitchen_data.postal_code else None
    if postal_code_value:
        digits_only = "".join(ch for ch in postal_code_value if ch.isdigit())
        if len(digits_only) == 5:
            postal_code_value = digits_only
    county_value = kitchen_data.county.strip() if kitchen_data.county else None

    if postal_code_value and (not state_value or not city_value or not county_value):
        resolved_location = resolve_by_zip(postal_code_value)
        resolved_state = resolved_location.get("state")
        resolved_city = resolved_location.get("city")
        resolved_county = resolved_location.get("county")

        if not state_value and resolved_state:
            state_value = resolved_state.upper()
        if not city_value and resolved_city:
            city_value = resolved_city
        if not county_value and resolved_county:
            county_value = resolved_county

    new_kitchen = Kitchen(
        name=kitchen_data.name,
        host_id=host_id,
        address=kitchen_data.address,
        description=kitchen_data.description,
        pricing=kitchen_data.pricing,
        equipment=kitchen_data.equipment,
        state=state_value,
        city=city_value,
        postal_code=postal_code_value,
        county=county_value,
        health_permit_number=kitchen_data.health_permit_number,
        last_inspection_date=kitchen_data.last_inspection_date,
        insurance_info=kitchen_data.insurance_info,
        zoning_type=kitchen_data.zoning_type,
        delivery_only=kitchen_data.delivery_only,
        permit_types=kitchen_data.permit_types,
    )

    db.add(new_kitchen)
    await db.commit()
    await db.refresh(new_kitchen)

    background_tasks.add_task(analyze_kitchen_compliance, str(new_kitchen.id))
    await _refresh_delivery_gauge(db)

    return _serialize_kitchen(new_kitchen)


@router.get("/{kitchen_id}", response_model=KitchenResponse)
async def get_kitchen(kitchen_id: str, db: AsyncSession = Depends(get_db)) -> KitchenResponse:
    """Retrieve a specific kitchen by its identifier."""

    kitchen = await _get_kitchen_or_404(db, kitchen_id)
    return _serialize_kitchen(kitchen)


@router.get("/", response_model=list[KitchenResponse])
async def list_kitchens(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[KitchenResponse]:
    """List kitchens with pagination support."""

    result = await db.execute(select(Kitchen).offset(skip).limit(limit))
    kitchens = result.scalars().all()
    await _refresh_delivery_gauge(db)
    return [_serialize_kitchen(kitchen) for kitchen in kitchens]


@router.get("/{kitchen_id}/sanitation", response_model=list[SanitationLogResponse])
async def list_sanitation_logs(
    kitchen_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[SanitationLogResponse]:
    """Return sanitation logs for a specific kitchen."""

    kitchen = await _get_kitchen_or_404(db, kitchen_id)
    result = await db.execute(
        select(SanitationLog)
        .where(SanitationLog.kitchen_id == kitchen.id)
        .order_by(desc(SanitationLog.logged_at))
    )
    entries = result.scalars().all()
    return [_serialize_sanitation_log(entry) for entry in entries]


@router.post(
    "/{kitchen_id}/sanitation",
    response_model=SanitationLogResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sanitation_log(
    kitchen_id: str,
    log_data: SanitationLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SanitationLogResponse:
    """Add a sanitation inspection record for a kitchen."""

    kitchen = await _get_kitchen_or_404(db, kitchen_id)

    # Verify ownership unless user is admin
    if not current_user.is_admin and str(kitchen.host_id) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this kitchen"
        )

    entry = SanitationLog(
        kitchen_id=kitchen.id,
        logged_at=log_data.logged_at or datetime.now(UTC),
        status=log_data.status,
        inspector_name=log_data.inspector_name,
        notes=log_data.notes,
        follow_up_required=log_data.follow_up_required,
    )

    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return _serialize_sanitation_log(entry)


@router.get("/{kitchen_id}/compliance", response_model=KitchenComplianceResponse)
async def get_kitchen_compliance(
    kitchen_id: str,
    db: AsyncSession = Depends(get_db),
) -> KitchenComplianceResponse:
    """Get the compliance status for a kitchen."""

    kitchen = await _get_kitchen_or_404(db, kitchen_id)

    location_context = _collect_location_context(kitchen)
    pilot_mode = is_pilot_location(
        state=kitchen.state,
        city=kitchen.city,
        county=location_context.get("county"),
        zip_code=location_context.get("zip_code"),
    )
    if pilot_mode:
        logger.debug(
            "Pilot mode enabled for kitchen compliance response",
            extra={
                "kitchen_id": kitchen_id,
                "zip_code": location_context.get("zip_code"),
                "county": location_context.get("county"),
            },
        )

    analyzer = RegulatoryAnalyzer()
    kitchen_payload = {
        "id": str(kitchen.id),
        "state": kitchen.state,
        "city": kitchen.city,
        "county": kitchen.county,
        "postal_code": kitchen.postal_code,
        "health_permit_number": kitchen.health_permit_number,
        "last_inspection_date": kitchen.last_inspection_date,
        "insurance": kitchen.insurance_info,
        "zoning_type": kitchen.zoning_type,
        "delivery_only": kitchen.delivery_only,
        "permit_types": kitchen.permit_types or [],
        "postal_code": location_context.get("zip_code"),
        "county": location_context.get("county"),
    }

    sanitation_stmt = (
        select(SanitationLog)
        .where(SanitationLog.kitchen_id == kitchen.id)
        .order_by(desc(SanitationLog.logged_at))
    )
    sanitation_rows = (await db.execute(sanitation_stmt)).scalars().all()
    kitchen_payload["sanitation_logs"] = [
        {
            "logged_at": log.logged_at,
            "status": log.status,
            "follow_up_required": log.follow_up_required,
        }
        for log in sanitation_rows
    ]

    regulations = await get_regulations_for_jurisdiction(db, kitchen.state, kitchen.city)
    analysis = await analyzer.analyze_kitchen_compliance(
        kitchen_payload, regulations, pilot_mode=pilot_mode
    )
    regulations = await get_regulations_for_jurisdiction(
        db,
        kitchen.state,
        kitchen.city,
        county=kitchen.county,
    )
    analysis = await analyzer.analyze_kitchen_compliance(kitchen_payload, regulations)

    settings = get_settings()
    if pilot_mode:
        banner = BOOKING_PILOT_BANNER
    elif settings.compliance_controls_enabled:
        banner = BOOKING_COMPLIANCE_BANNER
    else:
        banner = None

    override_allowed = pilot_mode

    host_user = kitchen.host
    subscription_status = SubscriptionStatus.INACTIVE.value
    trial_ends_at = None
    is_pilot_user = False
    if host_user is not None:
        subscription_status = host_user.subscription_status.value
        if host_user.trial_ends_at:
            trial_ends_at = host_user.trial_ends_at.isoformat()
        is_pilot_user = bool(host_user.is_pilot_user)

    return KitchenComplianceResponse(
        kitchen_id=str(kitchen.id),
        compliance_level=analysis.overall_compliance.value,
        risk_score=analysis.risk_score,
        missing_requirements=analysis.missing_requirements,
        recommendations=analysis.recommendations,
        last_analyzed=analysis.last_analyzed.isoformat(),
        city=kitchen.city,
        state=kitchen.state,
        county=kitchen.county,
        postal_code=kitchen.postal_code,
        booking_restrictions_banner=banner,
        delivery_only=kitchen.delivery_only,
        permit_types=kitchen.permit_types or [],
        last_sanitation_log=analysis.metadata.get("last_sanitation_log"),
        subscription_status=subscription_status,
        trial_ends_at=trial_ends_at,
        is_pilot_user=is_pilot_user,
        pilot_mode=pilot_mode,
        override_allowed=override_allowed,
    )


@router.get("/search/compliant", response_model=list[KitchenResponse])
async def search_compliant_kitchens(
    state: str,
    city: str | None = Query(default=None),
    min_compliance_level: str = Query("partial_compliance"),
    db: AsyncSession = Depends(get_db),
) -> list[KitchenResponse]:
    """Search for kitchens that meet a minimum compliance level."""

    allowed_levels = {"compliant", "partial_compliance", "non_compliant", "unknown"}
    if min_compliance_level not in allowed_levels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid compliance level filter"
        )

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid kitchen ID"
        ) from exc

    result = await db.execute(
        select(Kitchen).options(selectinload(Kitchen.host)).where(Kitchen.id == kitchen_uuid)
    )
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

        location_context = _collect_location_context(kitchen)
        pilot_mode = is_pilot_location(
            state=kitchen.state,
            city=kitchen.city,
            county=location_context.get("county"),
            zip_code=location_context.get("zip_code"),
        )
        if pilot_mode:
            logger.debug(
                "Pilot mode enabled during background compliance analysis",
                extra={
                    "kitchen_id": kitchen_id,
                    "zip_code": location_context.get("zip_code"),
                    "county": location_context.get("county"),
                },
            )

        analyzer = RegulatoryAnalyzer()
        kitchen_payload = {
            "id": str(kitchen.id),
            "state": kitchen.state,
            "city": kitchen.city,
            "county": kitchen.county,
            "postal_code": kitchen.postal_code,
            "health_permit_number": kitchen.health_permit_number,
            "last_inspection_date": kitchen.last_inspection_date,
            "insurance": kitchen.insurance_info,
            "zoning_type": kitchen.zoning_type,
            "delivery_only": kitchen.delivery_only,
            "permit_types": kitchen.permit_types or [],
            "postal_code": location_context.get("zip_code"),
            "county": location_context.get("county"),
        }
        sanitation_stmt = (
            select(SanitationLog)
            .where(SanitationLog.kitchen_id == kitchen.id)
            .order_by(desc(SanitationLog.logged_at))
        )
        sanitation_rows = (await session.execute(sanitation_stmt)).scalars().all()
        kitchen_payload["sanitation_logs"] = [
            {
                "logged_at": log.logged_at,
                "status": log.status,
                "follow_up_required": log.follow_up_required,
            }
            for log in sanitation_rows
        ]
        regulations = await get_regulations_for_jurisdiction(
            session,
            kitchen.state,
            kitchen.city,
            county=kitchen.county,
        )

        previous_status = kitchen.compliance_status or "unknown"
        analysis = await analyzer.analyze_kitchen_compliance(
            kitchen_payload, regulations, pilot_mode=pilot_mode
        )

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
