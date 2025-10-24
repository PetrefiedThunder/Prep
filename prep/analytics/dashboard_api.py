"""FastAPI router implementing the analytics dashboard API surface."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Dict, Mapping
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from prep.models import (
    AdminOverview,
    AdminUser,
    BookingAnalytics,
    ExportFormat,
    ExportResult,
    HostOverview,
    ReportType,
    RevenueAnalytics,
    TimeSeriesData,
    Timeframe,
    User,
)
from prep.models.analytics_models import (
    CancellationReason,
    KitchenPerformance,
    KitchenRevenue,
    PaymentMethodBreakdown,
    PlatformHealthMetrics,
    RecentBooking,
    RegionPerformance,
    TimeSlotPopularity,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class AnalyticsDashboardAPI:
    """Application service powering analytics dashboard endpoints."""

    def __init__(self) -> None:
        sample_host_id = UUID("aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa")
        second_host_id = UUID("bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb")
        self._host_overview: Dict[UUID, HostOverview] = {
            sample_host_id: self._build_sample_host_overview(sample_host_id),
            second_host_id: self._build_sample_host_overview(
                second_host_id,
                total_kitchens=4,
                active_kitchens=3,
                total_bookings=184,
                total_revenue=Decimal("84250.00"),
                average_rating=4.7,
                occupancy_rate=72.4,
                response_rate=97.0,
                last_30_days_revenue=Decimal("12450.00"),
            ),
        }
        self._booking_analytics: Dict[UUID, Mapping[Timeframe, BookingAnalytics]] = {
            host_id: self._build_sample_booking_analytics(host_id)
            for host_id in self._host_overview
        }
        self._revenue_analytics: Dict[UUID, Mapping[Timeframe, RevenueAnalytics]] = {
            host_id: self._build_sample_revenue_analytics(host_id)
            for host_id in self._host_overview
        }
        self._admin_overview = self._build_admin_overview()

    def _build_sample_host_overview(
        self,
        host_id: UUID,
        *,
        total_kitchens: int = 5,
        active_kitchens: int = 4,
        total_bookings: int = 215,
        total_revenue: Decimal = Decimal("112345.50"),
        average_rating: float = 4.5,
        occupancy_rate: float = 81.2,
        response_rate: float = 95.0,
        last_30_days_revenue: Decimal = Decimal("18450.00"),
    ) -> HostOverview:
        """Create deterministic overview metrics for a host."""

        base_time = datetime(2025, 1, 15, 12, tzinfo=UTC)
        host_suffix = host_id.hex[:6].upper()
        top_kitchen = KitchenPerformance(
            kitchen_id=uuid4(),
            kitchen_name=f"Skyline Culinary Studio {host_suffix}",
            bookings=92,
            revenue=Decimal("48215.25"),
            rating=4.8,
            occupancy_rate=87.5,
        )
        recent_bookings = [
            RecentBooking(
                booking_id=uuid4(),
                kitchen_id=top_kitchen.kitchen_id,
                kitchen_name=top_kitchen.kitchen_name,
                guest_name="Taylor Reed",
                start_time=base_time.replace(day=12, hour=18),
                end_time=base_time.replace(day=12, hour=22),
                status="completed",
                total_amount=Decimal("525.00"),
            ),
            RecentBooking(
                booking_id=uuid4(),
                kitchen_id=uuid4(),
                kitchen_name=f"Harborview Event Kitchen {host_suffix}",
                guest_name="Morgan Lee",
                start_time=base_time.replace(day=10, hour=9),
                end_time=base_time.replace(day=10, hour=13),
                status="confirmed",
                total_amount=Decimal("410.00"),
            ),
            RecentBooking(
                booking_id=uuid4(),
                kitchen_id=uuid4(),
                kitchen_name=f"Garden Terrace Kitchen {host_suffix}",
                guest_name="Avery Patel",
                start_time=base_time.replace(day=8, hour=16),
                end_time=base_time.replace(day=8, hour=20),
                status="completed",
                total_amount=Decimal("385.00"),
            ),
        ]
        return HostOverview(
            total_kitchens=total_kitchens,
            active_kitchens=active_kitchens,
            total_bookings=total_bookings,
            total_revenue=total_revenue,
            average_rating=average_rating,
            occupancy_rate=occupancy_rate,
            response_rate=response_rate,
            last_30_days_revenue=last_30_days_revenue,
            top_performing_kitchen=top_kitchen,
            recent_bookings=recent_bookings,
        )

    def _build_sample_booking_analytics(self, _host_id: UUID) -> Dict[Timeframe, BookingAnalytics]:
        """Return booking analytics for the supported timeframes."""

        base_date = datetime(2024, 12, 1, tzinfo=UTC).date()
        month_trend = [
            TimeSeriesData(date=base_date.replace(day=day), value=25 + (day % 5) * 3)
            for day in range(1, 31, 3)
        ]
        week_trend = month_trend[-3:]
        year_trend = [
            TimeSeriesData(date=base_date.replace(month=((i % 12) or 12)), value=180 + i * 7)
            for i in range(1, 13)
        ]
        base_analytics = BookingAnalytics(
            total_bookings=215,
            confirmed_bookings=198,
            cancelled_bookings=17,
            conversion_rate=68.2,
            booking_trends=month_trend,
            popular_time_slots=[
                TimeSlotPopularity(time_slot="10:00", booking_count=38),
                TimeSlotPopularity(time_slot="14:00", booking_count=46),
                TimeSlotPopularity(time_slot="19:00", booking_count=52),
            ],
            cancellation_reasons=[
                CancellationReason(reason="schedule_change", count=7),
                CancellationReason(reason="pricing", count=5),
                CancellationReason(reason="weather", count=3),
            ],
            guest_retention_rate=62.0,
        )
        return {
            Timeframe.MONTH: base_analytics,
            Timeframe.WEEK: base_analytics.model_copy(update={"booking_trends": week_trend, "total_bookings": 52}),
            Timeframe.YEAR: base_analytics.model_copy(update={"booking_trends": year_trend, "total_bookings": 2310}),
            Timeframe.DAY: base_analytics.model_copy(update={"booking_trends": month_trend[-1:], "total_bookings": 12}),
        }

    def _build_sample_revenue_analytics(self, _host_id: UUID) -> Dict[Timeframe, RevenueAnalytics]:
        """Return revenue analytics with deterministic series data."""

        base_date = datetime(2024, 12, 1, tzinfo=UTC).date()
        month_trend = [
            TimeSeriesData(date=base_date.replace(day=day), value=Decimal("4200") + Decimal(day * 75))
            for day in range(1, 31, 3)
        ]
        forecast = [
            TimeSeriesData(date=base_date.replace(month=((idx % 12) or 12)), value=Decimal("4500") + Decimal(idx * 120))
            for idx in range(1, 7)
        ]
        revenue_by_kitchen = [
            KitchenRevenue(
                kitchen_id=uuid4(),
                kitchen_name="Skyline Culinary Studio",
                total_revenue=Decimal("48215.25"),
                booking_count=92,
            ),
            KitchenRevenue(
                kitchen_id=uuid4(),
                kitchen_name="Harborview Event Kitchen",
                total_revenue=Decimal("32120.00"),
                booking_count=68,
            ),
            KitchenRevenue(
                kitchen_id=uuid4(),
                kitchen_name="Garden Terrace Kitchen",
                total_revenue=Decimal("21870.25"),
                booking_count=55,
            ),
        ]
        base_revenue = RevenueAnalytics(
            total_revenue=Decimal("112345.50"),
            revenue_trends=month_trend,
            revenue_by_kitchen=revenue_by_kitchen,
            average_booking_value=Decimal("415.25"),
            revenue_forecast=forecast,
            payment_methods_breakdown=[
                PaymentMethodBreakdown(method="card", percentage=68.0),
                PaymentMethodBreakdown(method="bank_transfer", percentage=21.0),
                PaymentMethodBreakdown(method="wallet", percentage=11.0),
            ],
        )
        return {
            Timeframe.MONTH: base_revenue,
            Timeframe.WEEK: base_revenue.model_copy(
                update={
                    "revenue_trends": month_trend[-3:],
                    "total_revenue": Decimal("17850.00"),
                }
            ),
            Timeframe.YEAR: base_revenue.model_copy(
                update={
                    "revenue_trends": [
                        TimeSeriesData(
                            date=base_date.replace(month=((idx % 12) or 12)),
                            value=Decimal("8200") + Decimal(idx * 320),
                        )
                        for idx in range(1, 13)
                    ],
                    "total_revenue": Decimal("982345.75"),
                }
            ),
            Timeframe.DAY: base_revenue.model_copy(
                update={
                    "revenue_trends": month_trend[-1:],
                    "total_revenue": Decimal("1420.00"),
                    "average_booking_value": Decimal("355.00"),
                }
            ),
        }

    def _build_admin_overview(self) -> AdminOverview:
        """Return the seeded admin overview analytics."""

        return AdminOverview(
            total_hosts=1280,
            total_kitchens=4520,
            total_bookings=198432,
            platform_revenue=Decimal("18452345.75"),
            active_users=28540,
            new_signups=1240,
            platform_health=PlatformHealthMetrics(
                api_uptime=99.95,
                average_response_time=235.0,
                error_rate=0.42,
                database_health="optimal",
                cache_hit_rate=94.5,
            ),
            top_performing_regions=[
                RegionPerformance(region="San Francisco Bay Area", bookings=1820, revenue=Decimal("214520.00"), growth_rate=8.5),
                RegionPerformance(region="New York Metro", bookings=1755, revenue=Decimal("205410.50"), growth_rate=7.8),
                RegionPerformance(region="Seattle", bookings=920, revenue=Decimal("112340.25"), growth_rate=6.1),
            ],
            pending_moderation=64,
        )

    def get_host_overview(self, host_id: UUID) -> HostOverview:
        """Fetch the overview analytics for a host."""

        try:
            return self._host_overview[host_id]
        except KeyError as exc:  # pragma: no cover - defensive branch
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Host {host_id} not found",
            ) from exc

    def get_host_booking_analytics(self, host_id: UUID, timeframe: Timeframe) -> BookingAnalytics:
        """Return booking analytics for the requested timeframe."""

        host_data = self._booking_analytics.get(host_id)
        if host_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Host {host_id} not found",
            )
        return host_data.get(timeframe, host_data[Timeframe.MONTH])

    def get_host_revenue_analytics(self, host_id: UUID, timeframe: Timeframe) -> RevenueAnalytics:
        """Return revenue analytics for the requested timeframe."""

        host_data = self._revenue_analytics.get(host_id)
        if host_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Host {host_id} not found",
            )
        return host_data.get(timeframe, host_data[Timeframe.MONTH])

    def get_admin_overview(self) -> AdminOverview:
        """Expose platform wide analytics for admins."""

        return self._admin_overview

    def export_analytics_data(self, report_type: ReportType, export_format: ExportFormat) -> ExportResult:
        """Simulate generating a downloadable analytics report."""

        generated_at = datetime.now(tz=UTC)
        expires_at = generated_at + timedelta(hours=1)
        download_url = (
            "https://cdn.prepchef.com/analytics/"
            f"{report_type.value}-{generated_at:%Y%m%d%H%M%S}.{export_format.value}"
        )
        return ExportResult(
            report_type=report_type,
            format=export_format,
            generated_at=generated_at,
            download_url=download_url,
            expires_at=expires_at,
        )


_analytics_api: AnalyticsDashboardAPI | None = None


def get_analytics_dashboard_api() -> AnalyticsDashboardAPI:
    """Dependency that returns a singleton analytics API instance."""

    global _analytics_api
    if _analytics_api is None:
        _analytics_api = AnalyticsDashboardAPI()
    return _analytics_api


async def get_current_user() -> User:
    """Dependency stub returning the authenticated user."""

    return User(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        email="host@example.com",
        full_name="Jordan Parker",
        roles=["host"],
    )


async def get_current_admin() -> AdminUser:
    """Dependency stub returning the authenticated admin user."""

    return AdminUser(
        id=UUID("22222222-2222-2222-2222-222222222222"),
        email="admin@example.com",
        full_name="Prep Admin",
        permissions=["analytics:view"],
    )


@router.get("/host/{host_id}/overview", response_model=HostOverview)
async def get_host_overview(
    host_id: UUID,
    current_user: User = Depends(get_current_user),
    api: AnalyticsDashboardAPI = Depends(get_analytics_dashboard_api),
) -> HostOverview:
    """Return the primary dashboard overview for the host."""

    _ = current_user
    return api.get_host_overview(host_id)


@router.get("/host/{host_id}/bookings", response_model=BookingAnalytics)
async def get_host_booking_analytics(
    host_id: UUID,
    timeframe: Timeframe = Query(Timeframe.MONTH),
    current_user: User = Depends(get_current_user),
    api: AnalyticsDashboardAPI = Depends(get_analytics_dashboard_api),
) -> BookingAnalytics:
    """Return booking analytics for the requested host and timeframe."""

    _ = current_user
    return api.get_host_booking_analytics(host_id, timeframe)


@router.get("/host/{host_id}/revenue", response_model=RevenueAnalytics)
async def get_host_revenue_analytics(
    host_id: UUID,
    timeframe: Timeframe = Query(Timeframe.MONTH),
    current_user: User = Depends(get_current_user),
    api: AnalyticsDashboardAPI = Depends(get_analytics_dashboard_api),
) -> RevenueAnalytics:
    """Return revenue analytics for the requested host and timeframe."""

    _ = current_user
    return api.get_host_revenue_analytics(host_id, timeframe)


@router.get("/admin/overview", response_model=AdminOverview)
async def get_admin_overview(
    current_admin: AdminUser = Depends(get_current_admin),
    api: AnalyticsDashboardAPI = Depends(get_analytics_dashboard_api),
) -> AdminOverview:
    """Return the administrator analytics overview."""

    _ = current_admin
    return api.get_admin_overview()


@router.get("/export/{report_type}", response_model=ExportResult)
async def export_analytics_data(
    report_type: ReportType,
    format: ExportFormat = Query(ExportFormat.CSV),
    current_user: User = Depends(get_current_user),
    api: AnalyticsDashboardAPI = Depends(get_analytics_dashboard_api),
) -> ExportResult:
    """Export analytics data in the requested format."""

    _ = current_user
    return api.export_analytics_data(report_type, format)
