"""FastAPI router exposing admin dashboard endpoints backed by PostgreSQL."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from prep.admin.dependencies import get_current_admin
from prep.admin.schemas import (
    CertificationDecisionRequest,
    CertificationDecisionResponse,
    CertificationListResponse,
    CertificationStats,
    CertificationSummary,
    ChecklistTemplateCreateRequest,
    ChecklistTemplateResponse,
    KitchenDetail,
    KitchenListResponse,
    KitchenModerationStats,
    KitchenSummary,
    ModerationDecision,
    ModerationRequest,
    ModerationResponse,
    PaginationMeta,
    SuspendUserRequest,
    UserListResponse,
    UserStats,
    UserSummary,
)
from prep.database import get_db
from prep.models.admin import AdminUser
from prep.models.db import (
    CertificationDocument,
    CertificationReviewStatus,
    ChecklistTemplate,
    Kitchen,
    ModerationStatus,
    User,
    UserRole,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post(
    "/checklist-template",
    response_model=ChecklistTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_checklist_template(
    payload: ChecklistTemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> ChecklistTemplateResponse:
    """Persist a new checklist template version for the admin console."""

    _ = current_admin

    result = await db.execute(
        select(func.max(ChecklistTemplate.version)).where(
            ChecklistTemplate.name == payload.name
        )
    )
    latest_version = result.scalar_one()
    next_version = (latest_version or 0) + 1

    template = ChecklistTemplate(
        name=payload.name,
        version=next_version,
        schema=payload.schema,
        description=payload.description,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    return ChecklistTemplateResponse.model_validate(template)


def _build_kitchen_summary(kitchen: Kitchen) -> KitchenSummary:
    """Convert a Kitchen ORM object into a summary schema."""

    host = kitchen.host
    return KitchenSummary(
        id=kitchen.id,
        name=kitchen.name,
        owner_id=host.id,
        owner_email=host.email,
        owner_name=host.full_name,
        location=kitchen.location,
        submitted_at=kitchen.submitted_at,
        moderation_status=kitchen.moderation_status,
        certification_status=kitchen.certification_status,
        trust_score=kitchen.trust_score,
        hourly_rate=kitchen.hourly_rate,
        moderated_at=kitchen.moderated_at,
    )


def _build_certification_summary(document: CertificationDocument) -> CertificationSummary:
    """Convert a CertificationDocument ORM object into a schema."""

    return CertificationSummary(
        id=document.id,
        kitchen_id=document.kitchen_id,
        kitchen_name=document.kitchen.name,
        document_type=document.document_type,
        document_url=document.document_url,
        status=document.status,
        submitted_at=document.submitted_at,
        verified_at=document.verified_at,
        reviewer_id=document.reviewer_id,
        rejection_reason=document.rejection_reason,
        expires_at=document.expires_at,
    )


async def _get_kitchen_or_404(db: AsyncSession, kitchen_id: UUID) -> Kitchen:
    """Fetch a kitchen with related host and certifications or raise 404."""

    result = await db.execute(
        select(Kitchen)
        .options(
            joinedload(Kitchen.host),
            joinedload(Kitchen.certifications),
        )
        .where(Kitchen.id == kitchen_id)
    )
    kitchen = result.unique().scalar_one_or_none()
    if kitchen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")
    return kitchen


@router.get("/kitchens/pending", response_model=KitchenListResponse)
async def get_pending_kitchens(
    *,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(default=None, description="Search by kitchen or host name"),
    owner_email: str | None = Query(default=None),
    certification_status: CertificationReviewStatus | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> KitchenListResponse:
    """Return the moderation queue for pending kitchens."""

    _ = current_admin  # Authentication already enforced

    filters = [Kitchen.moderation_status == ModerationStatus.PENDING]
    if certification_status:
        filters.append(Kitchen.certification_status == certification_status)
    if owner_email:
        filters.append(func.lower(User.email) == owner_email.lower())
    if search:
        pattern = f"%{search.lower()}%"
        filters.append(
            or_(
                func.lower(Kitchen.name).like(pattern),
                func.lower(User.full_name).like(pattern),
            )
        )

    total_stmt = (
        select(func.count())
        .select_from(Kitchen)
        .join(User)
        .where(and_(*filters))
    )
    result = await db.execute(total_stmt)
    total = result.scalar_one()

    query = (
        select(Kitchen)
        .options(joinedload(Kitchen.host))
        .join(User)
        .where(and_(*filters))
        .order_by(Kitchen.submitted_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    kitchens: Sequence[Kitchen] = result.scalars().unique().all()

    items = [_build_kitchen_summary(kitchen) for kitchen in kitchens]
    pagination = PaginationMeta(limit=limit, offset=offset, total=total)
    return KitchenListResponse(items=items, pagination=pagination)


@router.get("/kitchens/{kitchen_id}", response_model=KitchenDetail)
async def get_kitchen_details(
    kitchen_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> KitchenDetail:
    """Return the details for a specific kitchen awaiting moderation."""

    _ = current_admin
    kitchen = await _get_kitchen_or_404(db, kitchen_id)
    summary = _build_kitchen_summary(kitchen)
    certifications = [_build_certification_summary(doc) for doc in kitchen.certifications]
    return KitchenDetail(**summary.model_dump(), description=kitchen.description, rejection_reason=kitchen.rejection_reason, certifications=certifications)


@router.post("/kitchens/{kitchen_id}/moderate", response_model=ModerationResponse)
async def moderate_kitchen(
    kitchen_id: UUID,
    payload: ModerationRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> ModerationResponse:
    """Approve or reject a kitchen listing."""

    _ = current_admin
    kitchen = await _get_kitchen_or_404(db, kitchen_id)

    if kitchen.moderation_status != ModerationStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kitchen already moderated")

    now = datetime.now(timezone.utc)
    message: str

    if payload.action == ModerationDecision.APPROVE:
        kitchen.moderation_status = ModerationStatus.APPROVED
        kitchen.rejection_reason = None
        kitchen.is_active = True
        message = "Kitchen approved"
    elif payload.action == ModerationDecision.REJECT:
        kitchen.moderation_status = ModerationStatus.REJECTED
        kitchen.rejection_reason = payload.reason or "Rejected by administrator"
        kitchen.is_active = False
        message = "Kitchen rejected"
    else:
        kitchen.moderation_status = ModerationStatus.CHANGES_REQUESTED
        kitchen.rejection_reason = payload.reason or "Changes requested by administrator"
        message = "Changes requested"

    kitchen.moderated_at = now

    await db.commit()
    kitchen = await _get_kitchen_or_404(db, kitchen_id)

    summary = _build_kitchen_summary(kitchen)
    certifications = [_build_certification_summary(doc) for doc in kitchen.certifications]
    detail = KitchenDetail(
        **summary.model_dump(),
        description=kitchen.description,
        rejection_reason=kitchen.rejection_reason,
        certifications=certifications,
    )
    return ModerationResponse(kitchen=detail, message=message)


@router.get("/metrics/kitchens", response_model=KitchenModerationStats)
async def get_kitchen_moderation_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> KitchenModerationStats:
    """Return high-level moderation statistics."""

    _ = current_admin
    base_stmt = select(func.count()).select_from(Kitchen)

    total = (await db.execute(base_stmt)).scalar_one()
    pending = (
        await db.execute(base_stmt.where(Kitchen.moderation_status == ModerationStatus.PENDING))
    ).scalar_one()
    approved = (
        await db.execute(base_stmt.where(Kitchen.moderation_status == ModerationStatus.APPROVED))
    ).scalar_one()
    rejected = (
        await db.execute(base_stmt.where(Kitchen.moderation_status == ModerationStatus.REJECTED))
    ).scalar_one()
    changes_requested = (
        await db.execute(
            base_stmt.where(Kitchen.moderation_status == ModerationStatus.CHANGES_REQUESTED)
        )
    ).scalar_one()

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    approvals_last_7_days = (
        await db.execute(
            base_stmt.where(
                Kitchen.moderation_status == ModerationStatus.APPROVED,
                Kitchen.moderated_at >= seven_days_ago,
            )
        )
    ).scalar_one()

    return KitchenModerationStats(
        total=total,
        pending=pending,
        approved=approved,
        rejected=rejected,
        changes_requested=changes_requested,
        approvals_last_7_days=approvals_last_7_days,
    )


@router.get("/certifications/pending", response_model=CertificationListResponse)
async def get_pending_certifications(
    *,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    document_type: str | None = Query(default=None),
    search: str | None = Query(default=None, description="Search by kitchen name"),
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> CertificationListResponse:
    """Return pending certification documents for review."""

    _ = current_admin

    filters = [CertificationDocument.status == CertificationReviewStatus.PENDING]
    if document_type:
        filters.append(func.lower(CertificationDocument.document_type) == document_type.lower())
    if search:
        pattern = f"%{search.lower()}%"
        filters.append(func.lower(Kitchen.name).like(pattern))

    total_stmt = (
        select(func.count())
        .select_from(CertificationDocument)
        .join(Kitchen)
        .where(and_(*filters))
    )
    total = (await db.execute(total_stmt)).scalar_one()

    query = (
        select(CertificationDocument)
        .options(joinedload(CertificationDocument.kitchen))
        .join(Kitchen)
        .where(and_(*filters))
        .order_by(CertificationDocument.submitted_at.asc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    documents: Sequence[CertificationDocument] = result.scalars().unique().all()

    items = [_build_certification_summary(doc) for doc in documents]
    pagination = PaginationMeta(limit=limit, offset=offset, total=total)
    return CertificationListResponse(items=items, pagination=pagination)


@router.post("/certifications/{certification_id}/verify", response_model=CertificationDecisionResponse)
async def verify_certification(
    certification_id: UUID,
    payload: CertificationDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> CertificationDecisionResponse:
    """Approve or reject a pending certification document."""

    _ = current_admin

    result = await db.execute(
        select(CertificationDocument)
        .options(joinedload(CertificationDocument.kitchen))
        .where(CertificationDocument.id == certification_id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certification not found")

    if document.status != CertificationReviewStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Certification already reviewed")

    now = datetime.now(timezone.utc)
    if payload.approve:
        document.status = CertificationReviewStatus.APPROVED
        document.rejection_reason = None
        document.verified_at = now
        message = "Certification approved"
    else:
        if not payload.rejection_reason:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Rejection reason is required when rejecting a certification",
            )
        document.status = CertificationReviewStatus.REJECTED
        document.rejection_reason = payload.rejection_reason
        document.verified_at = now
        message = "Certification rejected"

    document.reviewer_id = current_admin.id

    await db.commit()
    document_result = await db.execute(
        select(CertificationDocument)
        .options(joinedload(CertificationDocument.kitchen))
        .where(CertificationDocument.id == certification_id)
    )
    updated_document = document_result.scalar_one()

    summary = _build_certification_summary(updated_document)
    return CertificationDecisionResponse(certification=summary, message=message)


@router.get("/certifications/stats", response_model=CertificationStats)
async def get_certification_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> CertificationStats:
    """Return aggregated certification metrics."""

    _ = current_admin
    base_stmt = select(func.count()).select_from(CertificationDocument)

    total = (await db.execute(base_stmt)).scalar_one()
    pending = (
        await db.execute(base_stmt.where(CertificationDocument.status == CertificationReviewStatus.PENDING))
    ).scalar_one()
    approved = (
        await db.execute(base_stmt.where(CertificationDocument.status == CertificationReviewStatus.APPROVED))
    ).scalar_one()
    rejected = (
        await db.execute(base_stmt.where(CertificationDocument.status == CertificationReviewStatus.REJECTED))
    ).scalar_one()

    soon_threshold = datetime.now(timezone.utc) + timedelta(days=30)
    expiring_soon = (
        await db.execute(
            base_stmt.where(
                CertificationDocument.status == CertificationReviewStatus.APPROVED,
                CertificationDocument.expires_at.is_not(None),
                CertificationDocument.expires_at <= soon_threshold,
            )
        )
    ).scalar_one()

    return CertificationStats(
        total=total,
        pending=pending,
        approved=approved,
        rejected=rejected,
        expiring_soon=expiring_soon,
    )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    *,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    role: UserRole | None = Query(default=None),
    include_suspended: bool = Query(False),
    search: str | None = Query(default=None, description="Search by name or email"),
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> UserListResponse:
    """Return a filtered list of users."""

    _ = current_admin

    filters = []
    if role:
        filters.append(User.role == role)
    if not include_suspended:
        filters.append(User.is_suspended.is_(False))
    if search:
        pattern = f"%{search.lower()}%"
        filters.append(
            or_(func.lower(User.email).like(pattern), func.lower(User.full_name).like(pattern))
        )

    stmt = select(func.count()).select_from(User)
    if filters:
        stmt = stmt.where(and_(*filters))
    total = (await db.execute(stmt)).scalar_one()

    query = select(User)
    if filters:
        query = query.where(and_(*filters))
    query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    users: Sequence[User] = result.scalars().all()

    items = [
        UserSummary(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
            is_suspended=user.is_suspended,
            suspension_reason=user.suspension_reason,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )
        for user in users
    ]
    pagination = PaginationMeta(limit=limit, offset=offset, total=total)
    return UserListResponse(items=items, pagination=pagination)


@router.post("/users/{user_id}/suspend", response_model=UserSummary)
async def suspend_user(
    user_id: UUID,
    payload: SuspendUserRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> UserSummary:
    """Suspend a user account."""

    _ = current_admin

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role == UserRole.ADMIN and user.id == current_admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Administrators cannot suspend themselves")

    user.is_suspended = True
    user.suspension_reason = payload.reason
    user.suspended_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user)

    return UserSummary(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        is_suspended=user.is_suspended,
        suspension_reason=user.suspension_reason,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.get("/users/stats", response_model=UserStats)
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> UserStats:
    """Return aggregated user metrics."""

    _ = current_admin

    base_stmt = select(func.count()).select_from(User)

    total = (await db.execute(base_stmt)).scalar_one()
    active = (
        await db.execute(base_stmt.where(User.is_active.is_(True), User.is_suspended.is_(False)))
    ).scalar_one()
    suspended = (
        await db.execute(base_stmt.where(User.is_suspended.is_(True)))
    ).scalar_one()
    admins = (
        await db.execute(base_stmt.where(User.role == UserRole.ADMIN))
    ).scalar_one()
    hosts = (
        await db.execute(base_stmt.where(User.role == UserRole.HOST))
    ).scalar_one()

    return UserStats(
        total=total,
        active=active,
        suspended=suspended,
        admins=admins,
        hosts=hosts,
    )
