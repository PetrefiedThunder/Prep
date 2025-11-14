"""Pydantic models supporting the analytics dashboard API."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class Timeframe(str, Enum):
    """Supported time windows for analytics queries."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class ExportFormat(str, Enum):
    """Available export formats for analytics data."""

    CSV = "csv"
    JSON = "json"
    PDF = "pdf"


class ReportType(str, Enum):
    """Types of analytics reports that may be exported."""

    HOST_OVERVIEW = "host_overview"
    BOOKINGS = "bookings"
    REVENUE = "revenue"
    ADMIN_OVERVIEW = "admin_overview"


class User(BaseModel):
    """Representation of an authenticated platform user."""

    id: UUID
    email: str
    full_name: str
    roles: list[str] = Field(default_factory=list)


class TimeSeriesData(BaseModel):
    """Value mapped to a specific calendar date."""

    date: date
    value: int | float | Decimal


class TimeSlotPopularity(BaseModel):
    """Aggregated booking counts by time of day."""

    time_slot: str
    booking_count: int = Field(ge=0)


class CancellationReason(BaseModel):
    """Distribution of cancellation reasons for bookings."""

    reason: str
    count: int = Field(ge=0)


class KitchenPerformance(BaseModel):
    """Performance snapshot for a specific kitchen."""

    kitchen_id: UUID
    kitchen_name: str
    bookings: int = Field(ge=0)
    revenue: Decimal = Field(ge=Decimal("0"))
    rating: float = Field(ge=0.0, le=5.0)
    occupancy_rate: float = Field(ge=0.0, le=100.0)


class RecentBooking(BaseModel):
    """Recent bookings used to populate host activity feeds."""

    booking_id: UUID
    kitchen_id: UUID
    kitchen_name: str
    guest_name: str
    start_time: datetime
    end_time: datetime
    status: str
    total_amount: Decimal = Field(ge=Decimal("0"))


class KitchenRevenue(BaseModel):
    """Revenue contribution from a single kitchen."""

    kitchen_id: UUID
    kitchen_name: str
    total_revenue: Decimal = Field(ge=Decimal("0"))
    booking_count: int = Field(ge=0)


class PaymentMethodBreakdown(BaseModel):
    """Share of revenue attributed to specific payment methods."""

    method: str
    percentage: float = Field(ge=0.0, le=100.0)


class RegionPerformance(BaseModel):
    """Regional performance metrics for the admin overview."""

    region: str
    bookings: int = Field(ge=0)
    revenue: Decimal = Field(ge=Decimal("0"))
    growth_rate: float


class PlatformHealthMetrics(BaseModel):
    """Operational health indicators for the platform."""

    api_uptime: float = Field(ge=0.0, le=100.0)
    average_response_time: float = Field(ge=0.0)
    error_rate: float = Field(ge=0.0, le=100.0)
    database_health: str
    cache_hit_rate: float = Field(ge=0.0, le=100.0)


class HostOverview(BaseModel):
    """Aggregate host performance metrics."""

    total_kitchens: int = Field(ge=0)
    active_kitchens: int = Field(ge=0)
    total_bookings: int = Field(ge=0)
    total_revenue: Decimal = Field(ge=Decimal("0"))
    average_rating: float = Field(ge=0.0, le=5.0)
    occupancy_rate: float = Field(ge=0.0, le=100.0)
    response_rate: float = Field(ge=0.0, le=100.0)
    last_30_days_revenue: Decimal = Field(ge=Decimal("0"))
    top_performing_kitchen: KitchenPerformance | None = None
    recent_bookings: list[RecentBooking] = Field(default_factory=list)


class BookingAnalytics(BaseModel):
    """Detailed booking funnel analytics for a host."""

    total_bookings: int = Field(ge=0)
    confirmed_bookings: int = Field(ge=0)
    cancelled_bookings: int = Field(ge=0)
    conversion_rate: float = Field(ge=0.0, le=100.0)
    booking_trends: list[TimeSeriesData] = Field(default_factory=list)
    popular_time_slots: list[TimeSlotPopularity] = Field(default_factory=list)
    cancellation_reasons: list[CancellationReason] = Field(default_factory=list)
    guest_retention_rate: float = Field(ge=0.0, le=100.0)


class RevenueAnalytics(BaseModel):
    """Revenue distribution and trend insights."""

    total_revenue: Decimal = Field(ge=Decimal("0"))
    revenue_trends: list[TimeSeriesData] = Field(default_factory=list)
    revenue_by_kitchen: list[KitchenRevenue] = Field(default_factory=list)
    average_booking_value: Decimal = Field(ge=Decimal("0"))
    revenue_forecast: list[TimeSeriesData] = Field(default_factory=list)
    payment_methods_breakdown: list[PaymentMethodBreakdown] = Field(default_factory=list)


class AdminOverview(BaseModel):
    """Platform wide analytics for administrators."""

    total_hosts: int = Field(ge=0)
    total_kitchens: int = Field(ge=0)
    total_bookings: int = Field(ge=0)
    platform_revenue: Decimal = Field(ge=Decimal("0"))
    active_users: int = Field(ge=0)
    new_signups: int = Field(ge=0)
    platform_health: PlatformHealthMetrics
    top_performing_regions: list[RegionPerformance] = Field(default_factory=list)
    pending_moderation: int = Field(ge=0)


class ExportResult(BaseModel):
    """Metadata describing a generated analytics export."""

    report_type: ReportType
    format: ExportFormat
    generated_at: datetime
    download_url: str
    expires_at: datetime


class PlatformOverviewMetrics(BaseModel):
    """High level platform analytics for executives."""

    total_users: int = Field(ge=0)
    total_hosts: int = Field(ge=0)
    total_kitchens: int = Field(ge=0)
    active_kitchens: int = Field(ge=0)
    total_bookings: int = Field(ge=0)
    total_revenue: Decimal = Field(ge=Decimal("0"))
    new_users_last_30_days: int = Field(ge=0)
    bookings_trend: list[TimeSeriesData] = Field(default_factory=list)
    revenue_trend: list[TimeSeriesData] = Field(default_factory=list)


class GrowthChannelBreakdown(BaseModel):
    """Acquisition contribution for a specific marketing channel."""

    channel: str
    signups: int = Field(ge=0)
    conversion_rate: float = Field(ge=0.0, le=100.0)


class PlatformGrowthMetrics(BaseModel):
    """User and host acquisition metrics."""

    user_signups: list[TimeSeriesData] = Field(default_factory=list)
    host_signups: list[TimeSeriesData] = Field(default_factory=list)
    conversion_rate: list[TimeSeriesData] = Field(default_factory=list)
    acquisition_channels: list[GrowthChannelBreakdown] = Field(default_factory=list)


class ModerationQueueMetrics(BaseModel):
    """Operational metrics for the moderation queue."""

    pending: int = Field(ge=0)
    in_review: int = Field(ge=0)
    escalated: int = Field(ge=0)
    sla_breaches: int = Field(ge=0)
    average_review_time_hours: float = Field(ge=0.0)
    moderation_trend: list[TimeSeriesData] = Field(default_factory=list)


class AdminTeamMemberPerformance(BaseModel):
    """Performance insights for an individual admin reviewer."""

    admin_id: UUID
    admin_name: str
    resolved_cases: int = Field(ge=0)
    average_resolution_time_hours: float = Field(ge=0.0)
    quality_score: float = Field(ge=0.0, le=100.0)


class AdminPerformanceMetrics(BaseModel):
    """Aggregated performance of the admin moderation team."""

    total_resolved: int = Field(ge=0)
    backlog: int = Field(ge=0)
    productivity_trend: list[TimeSeriesData] = Field(default_factory=list)
    team: list[AdminTeamMemberPerformance] = Field(default_factory=list)


class FinancialHealthMetrics(BaseModel):
    """Financial health indicators for the executive dashboard."""

    total_revenue: Decimal = Field(ge=Decimal("0"))
    net_revenue: Decimal = Field(ge=Decimal("0"))
    operational_expenses: Decimal = Field(ge=Decimal("0"))
    gross_margin: float = Field(ge=0.0, le=100.0)
    ebitda_margin: float = Field(ge=0.0, le=100.0)
    cash_on_hand: Decimal = Field(ge=Decimal("0"))
    burn_rate: Decimal = Field(ge=Decimal("0"))
    runway_months: float = Field(ge=0.0)
    revenue_trend: list[TimeSeriesData] = Field(default_factory=list)
    expense_trend: list[TimeSeriesData] = Field(default_factory=list)
