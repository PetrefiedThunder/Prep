"""Data models for the admin dashboard and moderation workflows."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class CertificationStatus(str, Enum):
    """Enumeration describing the certification lifecycle for a kitchen."""

    PENDING_UPLOAD = "pending_upload"
    PENDING_REVIEW = "pending_review"
    REVIEW_REQUIRED = "review_required"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ModerationAction(str, Enum):
    """Supported admin actions when moderating a kitchen listing."""

    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


class SortField(str, Enum):
    """Sortable fields exposed by the moderation queue API."""

    SUBMITTED_AT = "submitted_at"
    TRUST_SCORE = "trust_score"
    HOURLY_RATE = "hourly_rate"


class SortOrder(str, Enum):
    """Direction for sorting query results."""

    ASC = "asc"
    DESC = "desc"


class AdminUser(BaseModel):
    """Lightweight representation of an authenticated admin user."""

    id: UUID
    email: str
    full_name: str
    permissions: list[str] = Field(default_factory=list)


class PendingKitchen(BaseModel):
    """Serialized representation of a kitchen awaiting admin review."""

    id: UUID
    name: str
    host_id: UUID
    host_name: str
    host_email: str
    location: str
    submitted_at: datetime
    photos: list[str] = Field(default_factory=list)
    certification_status: CertificationStatus
    certification_type: str
    trust_score: float = Field(ge=0.0, le=5.0)
    equipment_count: int = Field(ge=0)
    hourly_rate: Decimal = Field(ge=Decimal("0"))
    status: str = "pending_review"


class ModerationFilters(BaseModel):
    """Filter controls accepted by the moderation queue endpoint."""

    status: str | None = None
    certification_status: CertificationStatus | None = None
    certification_type: str | None = None
    min_trust_score: float | None = Field(default=None, ge=0.0, le=5.0)
    submission_date_from: datetime | None = None
    submission_date_to: datetime | None = None

    @model_validator(mode="after")
    def _validate_date_range(self) -> ModerationFilters:
        """Ensure that the provided date window is sensible."""

        if (
            self.submission_date_from
            and self.submission_date_to
            and self.submission_date_from > self.submission_date_to
        ):
            raise ValueError("submission_date_from must be earlier than submission_date_to")
        return self


class Pagination(BaseModel):
    """Pagination and sorting controls for the moderation queue."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    sort_by: SortField = SortField.SUBMITTED_AT
    sort_order: SortOrder = SortOrder.DESC


class PendingKitchensResponse(BaseModel):
    """Envelope returned by the moderation queue endpoint."""

    kitchens: list[PendingKitchen] = Field(default_factory=list)
    total_count: int = Field(ge=0)
    has_more: bool


class ModerationRequest(BaseModel):
    """Request payload for the moderation endpoint."""

    action: ModerationAction
    reason: str | None = None
    notes: str | None = None


class ModerationResult(BaseModel):
    """Structured response returned after a moderation decision."""

    kitchen_id: UUID
    action: ModerationAction
    reason: str | None = None
    notes: str | None = None
    new_status: CertificationStatus
    processed_at: datetime


class PlatformOverview(BaseModel):
    """Aggregate analytics surfaced on the admin dashboard."""

    total_kitchens: int = Field(ge=0)
    active_kitchens: int = Field(ge=0)
    total_bookings: int = Field(ge=0)
    revenue_this_month: Decimal = Field(ge=Decimal("0"))
    conversion_rate: float = Field(ge=0.0)
    user_satisfaction: float = Field(ge=0.0, le=5.0)
    new_users_this_week: int = Field(ge=0)


class TimeSeriesPoint(BaseModel):
    """Normalized representation of a data point in a time series chart."""

    period: datetime
    value: Decimal


class KitchenPerformanceSummary(BaseModel):
    """Lightweight snapshot of an individual kitchen's performance."""

    kitchen_id: UUID
    kitchen_name: str
    total_bookings: int = Field(ge=0)
    revenue: Decimal = Field(ge=Decimal("0"))
    average_rating: float = Field(ge=0.0, le=5.0)


class HostPerformanceMetrics(BaseModel):
    """Aggregated metrics describing how a host is performing on the platform."""

    host_id: UUID
    host_name: str
    kitchen_count: int = Field(ge=0)
    active_kitchen_count: int = Field(ge=0)
    total_bookings: int = Field(ge=0)
    total_revenue: Decimal = Field(ge=Decimal("0"))
    average_rating: float = Field(ge=0.0, le=5.0)
    bookings_last_30_days: int = Field(ge=0)
    top_kitchens: list[KitchenPerformanceSummary] = Field(default_factory=list)


class BookingStatistics(BaseModel):
    """Booking level analytics used to populate dashboards and reports."""

    total_bookings: int = Field(ge=0)
    completed_bookings: int = Field(ge=0)
    cancelled_bookings: int = Field(ge=0)
    no_show_bookings: int = Field(ge=0)
    average_lead_time_hours: float = Field(ge=0.0)
    average_booking_value: Decimal = Field(ge=Decimal("0"))


class RevenueAnalytics(BaseModel):
    """Revenue specific analytics including trend data for visualizations."""

    total_revenue: Decimal = Field(ge=Decimal("0"))
    revenue_this_month: Decimal = Field(ge=Decimal("0"))
    month_over_month_growth: float
    revenue_trend: list[TimeSeriesPoint] = Field(default_factory=list)
    top_hosts: list[HostPerformanceMetrics] = Field(default_factory=list)
