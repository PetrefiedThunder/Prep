"""Database-backed FastAPI router for the admin dashboard."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from prep.auth import require_admin_role
from prep.database import get_db
from prep.models.orm import CertificationDocument, Kitchen, KitchenModerationEvent, User

router = APIRouter(prefix="/api/v1/admin", tags=["admin", "dashboard"])


class HostSummary(BaseModel):
    """Serialized summary of a kitchen host."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique identifier for the host")
    full_name: str = Field(..., description="Host full name")
    email: str = Field(..., description="Host contact email")


class KitchenListItem(BaseModel):
    """Compact representation of a kitchen awaiting review."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    city: str | None = None
    state: str | None = None
    hourly_rate: float | None = None
    trust_score: float | None = None
    moderation_status: str
    certification_status: str
    submitted_at: datetime
    host: HostSummary


class KitchenListResponse(BaseModel):
    """Envelope returned when listing pending kitchens."""

    kitchens: list[KitchenListItem] = Field(default_factory=list)
    total: int
    has_more: bool


class CertificationSummary(BaseModel):
    """Summary of a certification awaiting review."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kitchen_id: UUID
    kitchen_name: str
    document_type: str
    status: str
    uploaded_at: datetime
    expires_at: datetime | None = None
    file_url: str | None = None
    host_name: str
    host_email: str


class CertificationListResponse(BaseModel):
    """Envelope for pending certification documents."""

    certifications: list[CertificationSummary] = Field(default_factory=list)
    total: int
    has_more: bool


class ModerationEvent(BaseModel):
    """Individual moderation decision entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action: str
    reason: str | None = None
    notes: str | None = None
    created_at: datetime
    admin_id: UUID
    admin_name: str | None = Field(default=None, description="Name of the reviewing admin")


class CertificationDetail(BaseModel):
    """Detailed certification record for review."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_type: str
    status: str
    uploaded_at: datetime
    expires_at: datetime | None = None
    verified_at: datetime | None = None
    file_url: str | None = None
    rejection_reason: str | None = None


class KitchenDetailResponse(BaseModel):
    """Detailed representation of a kitchen and its review state."""

    id: UUID
    name: str
    description: str | None = None
    city: str | None = None
    state: str | None = None
    hourly_rate: float | None = None
    trust_score: float | None = None
    moderation_status: str
    certification_status: str
    submitted_at: datetime
    host: HostSummary
    certifications: list[CertificationDetail]
    moderation_history: list[ModerationEvent]


class ModerationRequest(BaseModel):
    """Request payload for moderating a kitchen."""

    action: str = Field(pattern="^(approve|reject|request_changes)$")
    reason: str | None = None
    notes: str | None = None


class ModerationResponse(BaseModel):
    """Response returned after moderating a kitchen."""

    kitchen_id: UUID
    action: str
    moderation_status: str
    certification_status: str
    processed_at: datetime


class KitchenStats(BaseModel):
    """Aggregate statistics for the moderation queue."""

    pending: int
    approved: int
    rejected: int
    changes_requested: int
    verified_kitchens: int
    published_kitchens: int
    avg_review_time_hours: float | None = None


class CertificationActionRequest(BaseModel):
    """Request to verify or reject a certification."""

    action: str = Field(pattern="^(verify|reject|request_updates)$")
    notes: str | None = None


class CertificationActionResponse(BaseModel):
    """Outcome returned after processing a certification."""

    certification_id: UUID
    action: str
    status: str
    verified_at: datetime | None = None
    rejection_reason: str | None = None


class CertificationStats(BaseModel):
    """Aggregate certification statistics."""

    pending: int
    verified: int
    rejected: int
    expiring_soon: int


class UserSummary(BaseModel):
    """Serialized representation of a platform user."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    is_active: bool
    is_admin: bool
    is_suspended: bool
    created_at: datetime
    last_login_at: datetime | None = None


class UserListResponse(BaseModel):
    """Envelope returned when listing users."""

    users: list[UserSummary]
    total: int
    has_more: bool


class SuspendUserRequest(BaseModel):
    """Payload describing why a user is being suspended."""

    reason: str | None = Field(default=None, max_length=500)


class SuspendUserResponse(BaseModel):
    """Response returned after suspending a user."""

    user_id: UUID
    suspended: bool
    processed_at: datetime
    reason: str | None = None


class UserStats(BaseModel):
    """Aggregate metrics for user accounts."""

    total: int
    active: int
    suspended: int
    admins: int


def _apply_kitchen_filters(
    base_conditions: list,
    *,
    city: str | None,
    state: str | None,
    certification_status: str | None,
    host_id: UUID | None,
    search: str | None,
) -> list:
    """Return SQLAlchemy conditions for kitchen filtering."""

    if city:
        base_conditions.append(func.lower(Kitchen.city) == city.lower())
    if state:
        base_conditions.append(func.lower(Kitchen.state) == state.lower())
    if certification_status:
        base_conditions.append(Kitchen.certification_status == certification_status)
    if host_id:
        base_conditions.append(Kitchen.host_id == host_id)
    if search:
        pattern = f"%{search.lower()}%"
        base_conditions.append(
            or_(
                func.lower(Kitchen.name).like(pattern),
                func.lower(User.full_name).like(pattern),
                func.lower(User.email).like(pattern),
            )
        )
    return base_conditions


def _load_host(kitchen: Kitchen) -> HostSummary:
    host = kitchen.host
    return HostSummary(id=host.id, full_name=host.full_name, email=host.email)


def _serialize_moderation_events(events: Iterable[KitchenModerationEvent]) -> list[ModerationEvent]:
    serialized: list[ModerationEvent] = []
    for event in events:
        serialized.append(
            ModerationEvent(
                id=event.id,
                action=event.action,
                reason=event.reason,
                notes=event.notes,
                created_at=event.created_at,
                admin_id=event.admin_id,
                admin_name=event.admin.full_name if event.admin else None,
            )
        )
    return serialized


def _serialize_certifications(
    documents: Iterable[CertificationDocument],
) -> list[CertificationDetail]:
    serialized: list[CertificationDetail] = []
    for document in documents:
        serialized.append(
            CertificationDetail(
                id=document.id,
                document_type=document.document_type,
                status=document.status,
                uploaded_at=document.created_at,
                expires_at=document.expires_at,
                verified_at=document.verified_at,
                file_url=document.file_url,
                rejection_reason=document.rejection_reason,
            )
        )
    return serialized


@router.get("/kitchens/pending", response_model=KitchenListResponse)
async def list_pending_kitchens(
    *,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    city: str | None = Query(default=None),
    state: str | None = Query(default=None),
    certification_status: str | None = Query(default=None),
    host_id: UUID | None = Query(default=None),
    search: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_role),  # noqa: ARG001 - dependency usage
) -> KitchenListResponse:
    """Return kitchens that are awaiting moderation."""

    conditions = _apply_kitchen_filters(
        [Kitchen.moderation_status == "pending"],
        city=city,
        state=state,
        certification_status=certification_status,
        host_id=host_id,
        search=search,
    )

    base_ids_stmt = select(Kitchen.id).join(User).where(and_(*conditions))
    count_stmt = select(func.count()).select_from(base_ids_stmt.subquery())
    total = int(await db.scalar(count_stmt) or 0)

    data_stmt = (
        select(Kitchen)
        .options(selectinload(Kitchen.host))
        .join(User)
        .where(and_(*conditions))
        .order_by(Kitchen.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    kitchens = (await db.scalars(data_stmt)).unique().all()

    serialized = [
        KitchenListItem(
            id=kitchen.id,
            name=kitchen.name,
            city=kitchen.city,
            state=kitchen.state,
            hourly_rate=float(kitchen.hourly_rate) if kitchen.hourly_rate is not None else None,
            trust_score=kitchen.trust_score,
            moderation_status=kitchen.moderation_status,
            certification_status=kitchen.certification_status,
            submitted_at=kitchen.created_at,
            host=_load_host(kitchen),
        )
        for kitchen in kitchens
    ]

    has_more = offset + len(serialized) < total
    return KitchenListResponse(kitchens=serialized, total=total, has_more=has_more)


@router.get("/kitchens/{kitchen_id}", response_model=KitchenDetailResponse)
async def get_kitchen_detail(
    kitchen_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_role),  # noqa: ARG001 - dependency usage
) -> KitchenDetailResponse:
    """Return detailed information for a specific kitchen."""

    stmt = (
        select(Kitchen)
        .options(
            selectinload(Kitchen.host),
            selectinload(Kitchen.certifications),
            selectinload(Kitchen.moderation_events).selectinload(KitchenModerationEvent.admin),
        )
        .where(Kitchen.id == kitchen_id)
    )

    kitchen = (await db.scalars(stmt)).first()
    if kitchen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")

    return KitchenDetailResponse(
        id=kitchen.id,
        name=kitchen.name,
        description=kitchen.description,
        city=kitchen.city,
        state=kitchen.state,
        hourly_rate=float(kitchen.hourly_rate) if kitchen.hourly_rate is not None else None,
        trust_score=kitchen.trust_score,
        moderation_status=kitchen.moderation_status,
        certification_status=kitchen.certification_status,
        submitted_at=kitchen.created_at,
        host=_load_host(kitchen),
        certifications=_serialize_certifications(kitchen.certifications),
        moderation_history=_serialize_moderation_events(kitchen.moderation_events),
    )


def _resolve_moderation_transition(action: str) -> tuple[str, str]:
    mapping = {
        "approve": ("approved", "verified"),
        "reject": ("rejected", "rejected"),
        "request_changes": ("changes_requested", "review_required"),
    }
    try:
        return mapping[action]
    except KeyError as exc:  # pragma: no cover - guarded by validation
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported action"
        ) from exc


@router.post("/kitchens/{kitchen_id}/moderate", response_model=ModerationResponse)
async def moderate_kitchen(
    kitchen_id: UUID,
    payload: ModerationRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_role),
) -> ModerationResponse:
    """Apply a moderation decision to a kitchen listing."""

    kitchen = await db.get(Kitchen, kitchen_id)
    if kitchen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")

    new_moderation_status, new_cert_status = _resolve_moderation_transition(payload.action)

    event = KitchenModerationEvent(
        kitchen_id=kitchen.id,
        admin_id=current_admin.id,
        action=payload.action,
        reason=payload.reason,
        notes=payload.notes,
    )
    kitchen.moderation_status = new_moderation_status
    kitchen.certification_status = new_cert_status
    if payload.action == "approve":
        kitchen.published = True

    db.add(event)
    await db.commit()
    await db.refresh(kitchen)

    return ModerationResponse(
        kitchen_id=kitchen.id,
        action=payload.action,
        moderation_status=kitchen.moderation_status,
        certification_status=kitchen.certification_status,
        processed_at=event.created_at,
    )


@router.get("/kitchens/stats", response_model=KitchenStats)
async def get_kitchen_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_role),  # noqa: ARG001 - dependency usage
) -> KitchenStats:
    """Return aggregate moderation statistics."""

    async def _count(condition) -> int:
        stmt = select(func.count()).select_from(Kitchen).where(condition)
        return int(await db.scalar(stmt) or 0)

    pending = await _count(Kitchen.moderation_status == "pending")
    approved = await _count(Kitchen.moderation_status == "approved")
    rejected = await _count(Kitchen.moderation_status == "rejected")
    changes_requested = await _count(Kitchen.moderation_status == "changes_requested")
    verified = await _count(Kitchen.certification_status == "verified")
    published = await _count(Kitchen.published.is_(True))

    avg_stmt = (
        select(
            func.avg(func.extract("epoch", KitchenModerationEvent.created_at - Kitchen.created_at))
        )
        .join(Kitchen, KitchenModerationEvent.kitchen_id == Kitchen.id)
        .where(KitchenModerationEvent.action.in_(["approve", "reject"]))
    )
    avg_seconds = await db.scalar(avg_stmt)
    avg_hours = round(float(avg_seconds) / 3600, 2) if avg_seconds else None

    return KitchenStats(
        pending=pending,
        approved=approved,
        rejected=rejected,
        changes_requested=changes_requested,
        verified_kitchens=verified,
        published_kitchens=published,
        avg_review_time_hours=avg_hours,
    )


@router.get("/certifications/pending", response_model=CertificationListResponse)
async def list_pending_certifications(
    *,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    document_type: str | None = Query(default=None),
    kitchen_id: UUID | None = Query(default=None),
    expires_before: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_role),  # noqa: ARG001 - dependency usage
) -> CertificationListResponse:
    """List certification documents awaiting verification."""

    conditions = [CertificationDocument.status.in_(["pending", "submitted", "renewal_requested"])]
    if document_type:
        conditions.append(CertificationDocument.document_type == document_type)
    if kitchen_id:
        conditions.append(CertificationDocument.kitchen_id == kitchen_id)
    if expires_before:
        conditions.append(CertificationDocument.expires_at <= expires_before)

    base_stmt = select(CertificationDocument.id).where(and_(*conditions))
    total = int(await db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0)

    data_stmt = (
        select(CertificationDocument)
        .options(selectinload(CertificationDocument.kitchen).selectinload(Kitchen.host))
        .where(and_(*conditions))
        .order_by(CertificationDocument.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    results = (await db.scalars(data_stmt)).unique().all()

    serialized: list[CertificationSummary] = []
    for document in results:
        kitchen = document.kitchen
        host = kitchen.host
        serialized.append(
            CertificationSummary(
                id=document.id,
                kitchen_id=document.kitchen_id,
                kitchen_name=kitchen.name,
                document_type=document.document_type,
                status=document.status,
                uploaded_at=document.created_at,
                expires_at=document.expires_at,
                file_url=document.file_url,
                host_name=host.full_name,
                host_email=host.email,
            )
        )

    has_more = offset + len(serialized) < total
    return CertificationListResponse(certifications=serialized, total=total, has_more=has_more)


def _map_certification_action(action: str) -> str:
    mapping = {
        "verify": "verified",
        "reject": "rejected",
        "request_updates": "pending_additional_info",
    }
    try:
        return mapping[action]
    except KeyError as exc:  # pragma: no cover - guarded by validation
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported action"
        ) from exc


@router.post(
    "/certifications/{certification_id}/verify", response_model=CertificationActionResponse
)
async def process_certification(
    certification_id: UUID,
    payload: CertificationActionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_role),  # noqa: ARG001 - dependency usage
) -> CertificationActionResponse:
    """Verify or reject a certification document."""

    document = await db.get(CertificationDocument, certification_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certification not found")

    target_status = _map_certification_action(payload.action)
    document.status = target_status
    now = datetime.now(UTC)

    if payload.action == "verify":
        document.verified_at = now
        document.rejection_reason = None
    elif payload.action == "reject":
        document.rejection_reason = payload.notes
        document.verified_at = None
    else:  # request_updates
        document.rejection_reason = payload.notes
        document.verified_at = None

    kitchen = await db.get(Kitchen, document.kitchen_id)
    if kitchen:
        kitchen.certification_status = (
            "verified" if payload.action == "verify" else kitchen.certification_status
        )

    await db.commit()
    return CertificationActionResponse(
        certification_id=document.id,
        action=payload.action,
        status=document.status,
        verified_at=document.verified_at,
        rejection_reason=document.rejection_reason,
    )


@router.get("/certifications/stats", response_model=CertificationStats)
async def get_certification_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_role),  # noqa: ARG001 - dependency usage
) -> CertificationStats:
    """Return aggregate metrics for certification processing."""

    status_counts = dict(
        await db.execute(
            select(CertificationDocument.status, func.count()).group_by(
                CertificationDocument.status
            )
        )
    )
    pending = int(
        status_counts.get("pending", 0)
        + status_counts.get("submitted", 0)
        + status_counts.get("renewal_requested", 0)
    )
    verified = int(status_counts.get("verified", 0))
    rejected = int(status_counts.get("rejected", 0))

    soon_stmt = (
        select(func.count())
        .select_from(CertificationDocument)
        .where(
            and_(
                CertificationDocument.expires_at.isnot(None),
                CertificationDocument.expires_at <= datetime.now(UTC) + timedelta(days=30),
            )
        )
    )
    expiring_soon = int(await db.scalar(soon_stmt) or 0)

    return CertificationStats(
        pending=pending,
        verified=verified,
        rejected=rejected,
        expiring_soon=expiring_soon,
    )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    *,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = Query(default=None),
    status_filter: str | None = Query(alias="status", default=None),
    role: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_role),  # noqa: ARG001 - dependency usage
) -> UserListResponse:
    """List platform users with optional filtering."""

    conditions: list = []
    if search:
        pattern = f"%{search.lower()}%"
        conditions.append(
            or_(
                func.lower(User.email).like(pattern),
                func.lower(User.full_name).like(pattern),
            )
        )
    if status_filter == "active":
        conditions.append(and_(User.is_active.is_(True), User.is_suspended.is_(False)))
    elif status_filter == "suspended":
        conditions.append(User.is_suspended.is_(True))
    elif status_filter == "inactive":
        conditions.append(User.is_active.is_(False))
    if role == "admin":
        conditions.append(User.is_admin.is_(True))
    elif role == "host":
        conditions.append(User.is_admin.is_(False))

    stmt = select(User).order_by(User.created_at.desc())
    if conditions:
        stmt = stmt.where(and_(*conditions))

    total = int(await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    users = (await db.scalars(stmt.offset(offset).limit(limit))).all()

    summaries = [
        UserSummary(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            is_suspended=user.is_suspended,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
        for user in users
    ]

    has_more = offset + len(summaries) < total
    return UserListResponse(users=summaries, total=total, has_more=has_more)


@router.post("/users/{user_id}/suspend", response_model=SuspendUserResponse)
async def suspend_user(
    user_id: UUID,
    payload: SuspendUserRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_role),  # noqa: ARG001 - dependency usage
) -> SuspendUserResponse:
    """Suspend a user account that violates platform policies."""

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_suspended = True
    user.is_active = False

    await db.commit()
    processed_at = datetime.now(UTC)
    return SuspendUserResponse(
        user_id=user.id, suspended=True, processed_at=processed_at, reason=payload.reason
    )


@router.get("/users/stats", response_model=UserStats)
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_admin_role),  # noqa: ARG001 - dependency usage
) -> UserStats:
    """Return aggregate statistics for platform users."""

    total_users = int(await db.scalar(select(func.count()).select_from(User)) or 0)
    suspended = int(
        await db.scalar(select(func.count()).select_from(User).where(User.is_suspended.is_(True)))
        or 0
    )
    admins = int(
        await db.scalar(select(func.count()).select_from(User).where(User.is_admin.is_(True))) or 0
    )
    active = total_users - suspended

    return UserStats(total=total_users, active=active, suspended=suspended, admins=admins)
