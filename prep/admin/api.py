"""FastAPI router exposing admin dashboard endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Dict, List, Sequence
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError

from prep.models.admin import (
    CertificationStatus,
    ModerationAction,
    ModerationFilters,
    ModerationRequest,
    ModerationResult,
    Pagination,
    PendingKitchen,
    PendingKitchensResponse,
    PlatformOverview,
    SortField,
    SortOrder,
)

router = APIRouter(prefix="/api/v1", tags=["admin"])


def _generate_sample_kitchens() -> List[PendingKitchen]:
    """Return a deterministic set of sample kitchens used for defaults."""

    submitted = datetime(2025, 10, 20, 10, 0, tzinfo=UTC)
    return [
        PendingKitchen(
            id=uuid4(),
            name="Sunset Loft Kitchen",
            host_id=uuid4(),
            host_name="Ava Johnson",
            host_email="ava@example.com",
            location="San Francisco, CA",
            submitted_at=submitted,
            photos=[
                "https://cdn.prepchef.com/kitchens/sunrise-loft/thumb1.jpg",
                "https://cdn.prepchef.com/kitchens/sunrise-loft/thumb2.jpg",
            ],
            certification_status=CertificationStatus.PENDING_REVIEW,
            certification_type="health_department",
            trust_score=4.2,
            equipment_count=18,
            hourly_rate=Decimal("115.00"),
            status="pending_review",
        ),
        PendingKitchen(
            id=uuid4(),
            name="Harborview Test Kitchen",
            host_id=uuid4(),
            host_name="Miguel Santos",
            host_email="miguel@example.com",
            location="Seattle, WA",
            submitted_at=submitted.replace(hour=12),
            photos=["https://cdn.prepchef.com/kitchens/harborview/thumb1.jpg"],
            certification_status=CertificationStatus.PENDING_UPLOAD,
            certification_type="food_handler",
            trust_score=3.8,
            equipment_count=12,
            hourly_rate=Decimal("85.00"),
            status="pending_review",
        ),
        PendingKitchen(
            id=uuid4(),
            name="Brooklyn Artisan Kitchen",
            host_id=uuid4(),
            host_name="Danielle Rivers",
            host_email="danielle@example.com",
            location="Brooklyn, NY",
            submitted_at=submitted.replace(day=19, hour=16),
            photos=["https://cdn.prepchef.com/kitchens/brooklyn-artisan/thumb1.jpg"],
            certification_status=CertificationStatus.REVIEW_REQUIRED,
            certification_type="safety_audit",
            trust_score=4.7,
            equipment_count=22,
            hourly_rate=Decimal("140.00"),
            status="request_changes",
        ),
    ]


class AdminDashboardAPI:
    """Application service powering admin moderation workflows."""

    def __init__(
        self,
        *,
        pending_kitchens: Sequence[PendingKitchen] | None = None,
        overview_seed: PlatformOverview | None = None,
    ) -> None:
        self._pending_kitchens: List[PendingKitchen] = [
            kitchen.model_copy(deep=True) for kitchen in (pending_kitchens or _generate_sample_kitchens())
        ]
        self._all_kitchens: Dict[UUID, PendingKitchen] = {
            kitchen.id: kitchen.model_copy(deep=True) for kitchen in self._pending_kitchens
        }
        self._moderation_history: List[ModerationResult] = []
        self._overview_seed = overview_seed or PlatformOverview(
            total_kitchens=len(self._pending_kitchens),
            active_kitchens=0,
            total_bookings=525,
            revenue_this_month=Decimal("24875.00"),
            conversion_rate=0.21,
            user_satisfaction=4.6,
            new_users_this_week=37,
        )

    def _filter_pending(self, filters: ModerationFilters) -> List[PendingKitchen]:
        """Apply moderation filters to the in-memory queue."""

        kitchens = list(self._pending_kitchens)

        if filters.status:
            kitchens = [kitchen for kitchen in kitchens if kitchen.status == filters.status]
        if filters.certification_status:
            kitchens = [
                kitchen
                for kitchen in kitchens
                if kitchen.certification_status == filters.certification_status
            ]
        if filters.certification_type:
            kitchens = [
                kitchen for kitchen in kitchens if kitchen.certification_type == filters.certification_type
            ]
        if filters.min_trust_score is not None:
            kitchens = [kitchen for kitchen in kitchens if kitchen.trust_score >= filters.min_trust_score]
        if filters.submission_date_from:
            kitchens = [
                kitchen for kitchen in kitchens if kitchen.submitted_at >= filters.submission_date_from
            ]
        if filters.submission_date_to:
            kitchens = [
                kitchen for kitchen in kitchens if kitchen.submitted_at <= filters.submission_date_to
            ]

        return kitchens

    @staticmethod
    def _sort_kitchens(kitchens: List[PendingKitchen], pagination: Pagination) -> List[PendingKitchen]:
        """Return kitchens sorted using the requested pagination options."""

        sort_key_map = {
            SortField.SUBMITTED_AT: lambda kitchen: kitchen.submitted_at,
            SortField.TRUST_SCORE: lambda kitchen: kitchen.trust_score,
            SortField.HOURLY_RATE: lambda kitchen: kitchen.hourly_rate,
        }
        key = sort_key_map[pagination.sort_by]
        reverse = pagination.sort_order == SortOrder.DESC
        return sorted(kitchens, key=key, reverse=reverse)

    def get_pending_kitchens(
        self,
        filters: ModerationFilters,
        pagination: Pagination,
    ) -> PendingKitchensResponse:
        """Retrieve pending kitchens honouring filters and pagination."""

        kitchens = self._filter_pending(filters)
        total_count = len(kitchens)
        kitchens = self._sort_kitchens(kitchens, pagination)
        start = pagination.offset
        end = start + pagination.limit
        window = kitchens[start:end]
        has_more = end < total_count

        return PendingKitchensResponse(kitchens=window, total_count=total_count, has_more=has_more)

    def _resolve_status_from_action(self, action: ModerationAction) -> CertificationStatus:
        """Map a moderation action to the resulting certification status."""

        if action is ModerationAction.APPROVE:
            return CertificationStatus.VERIFIED
        if action is ModerationAction.REJECT:
            return CertificationStatus.REJECTED
        return CertificationStatus.REVIEW_REQUIRED

    def moderate_kitchen(
        self,
        kitchen_id: str | UUID,
        action: ModerationAction,
        reason: str | None = None,
        notes: str | None = None,
    ) -> ModerationResult:
        """Apply a moderation decision to a kitchen listing."""

        kitchen_uuid = UUID(str(kitchen_id))
        pending_index = next(
            (index for index, kitchen in enumerate(self._pending_kitchens) if kitchen.id == kitchen_uuid),
            None,
        )
        if pending_index is None:
            raise LookupError(f"Kitchen {kitchen_uuid} is not awaiting moderation")

        kitchen = self._pending_kitchens[pending_index]
        new_status = self._resolve_status_from_action(action)
        updated_kitchen = kitchen.model_copy(update={"certification_status": new_status, "status": kitchen.status})

        if action in {ModerationAction.APPROVE, ModerationAction.REJECT}:
            self._pending_kitchens.pop(pending_index)
        else:
            self._pending_kitchens[pending_index] = updated_kitchen

        self._all_kitchens[kitchen_uuid] = updated_kitchen
        result = ModerationResult(
            kitchen_id=kitchen_uuid,
            action=action,
            reason=reason,
            notes=notes,
            new_status=new_status,
            processed_at=datetime.now(tz=UTC),
        )
        self._moderation_history.append(result)
        return result

    def get_platform_overview(self) -> PlatformOverview:
        """Compute a lightweight platform overview for the dashboard."""

        overview = self._overview_seed.model_copy(deep=True)
        overview.total_kitchens = len(self._all_kitchens)
        overview.active_kitchens = sum(
            1 for kitchen in self._all_kitchens.values() if kitchen.certification_status == CertificationStatus.VERIFIED
        )
        return overview

    @property
    def pending_kitchens(self) -> Sequence[PendingKitchen]:
        """Expose the active moderation queue for inspection in tests."""

        return tuple(self._pending_kitchens)


_DEFAULT_API = AdminDashboardAPI()


def get_admin_dashboard_api() -> AdminDashboardAPI:
    """FastAPI dependency returning the shared admin dashboard service."""

    return _DEFAULT_API


@router.get("/admin/kitchens/pending", response_model=PendingKitchensResponse)
async def get_pending_kitchens(
    status: str | None = Query(default=None, description="Filter by listing workflow status"),
    certification_status: CertificationStatus | None = Query(
        default=None, description="Filter by certification review status"
    ),
    certification_type: str | None = Query(default=None, description="Filter by certification document type"),
    min_trust_score: float | None = Query(
        default=None,
        ge=0.0,
        le=5.0,
        description="Filter kitchens by minimum host trust score",
    ),
    submitted_after: datetime | None = Query(
        default=None, description="Return kitchens submitted on or after this timestamp"
    ),
    submitted_before: datetime | None = Query(
        default=None, description="Return kitchens submitted on or before this timestamp"
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: SortField = Query(default=SortField.SUBMITTED_AT),
    sort_order: SortOrder = Query(default=SortOrder.DESC),
    admin_api: AdminDashboardAPI = Depends(get_admin_dashboard_api),
) -> PendingKitchensResponse:
    """Get kitchens pending admin approval."""

    try:
        filters = ModerationFilters(
            status=status,
            certification_status=certification_status,
            certification_type=certification_type,
            min_trust_score=min_trust_score,
            submission_date_from=submitted_after,
            submission_date_to=submitted_before,
        )
        pagination = Pagination(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except ValidationError as exc:  # pragma: no cover - FastAPI already validates query params
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    return admin_api.get_pending_kitchens(filters, pagination)


@router.post("/admin/kitchens/{kitchen_id}/moderate", response_model=ModerationResult)
async def moderate_kitchen(
    kitchen_id: str,
    request: ModerationRequest,
    admin_api: AdminDashboardAPI = Depends(get_admin_dashboard_api),
) -> ModerationResult:
    """Moderate a kitchen listing."""

    try:
        return admin_api.moderate_kitchen(
            kitchen_id=kitchen_id,
            action=request.action,
            reason=request.reason,
            notes=request.notes,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/admin/analytics/overview", response_model=PlatformOverview)
async def get_platform_overview(
    admin_api: AdminDashboardAPI = Depends(get_admin_dashboard_api),
) -> PlatformOverview:
    """Get platform-wide analytics overview."""

    return admin_api.get_platform_overview()
