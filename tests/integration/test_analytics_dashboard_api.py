from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from prep.analytics.dashboard_api import get_dashboard_service, router as analytics_router
from prep.auth import get_current_admin as auth_get_current_admin
from prep.models.pydantic_exports import (
    AdminPerformanceMetrics,
    AdminTeamMemberPerformance,
    FinancialHealthMetrics,
    GrowthChannelBreakdown,
    KitchenRevenue,
    ModerationQueueMetrics,
    PaymentMethodBreakdown,
    PlatformGrowthMetrics,
    PlatformOverviewMetrics,
    RegionPerformance,
    RevenueAnalytics,
    TimeSeriesData,
)

os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///:memory:'

pytestmark = pytest.mark.anyio('asyncio')


class StubAnalyticsDashboardService:
    """Analytics dashboard service returning deterministic payloads for testing."""

    def __init__(self) -> None:
        today = date.today()
        yesterday = today.replace(day=max(1, today.day - 1))
        self._overview = PlatformOverviewMetrics(
            total_users=1200,
            total_hosts=120,
            total_kitchens=85,
            active_kitchens=80,
            total_bookings=5400,
            total_revenue=Decimal('125000.00'),
            new_users_last_30_days=120,
            bookings_trend=[TimeSeriesData(date=yesterday, value=180), TimeSeriesData(date=today, value=220)],
            revenue_trend=[
                TimeSeriesData(date=yesterday, value=Decimal('14500.00')),
                TimeSeriesData(date=today, value=Decimal('15250.25')),
            ],
        )
        self._revenue = RevenueAnalytics(
            total_revenue=Decimal('125000.00'),
            revenue_trends=[TimeSeriesData(date=today, value=Decimal('15250.25'))],
            revenue_by_kitchen=[
                KitchenRevenue(
                    kitchen_id=uuid4(),
                    kitchen_name='Downtown Kitchen',
                    total_revenue=Decimal('45250.50'),
                    booking_count=120,
                ),
                KitchenRevenue(
                    kitchen_id=uuid4(),
                    kitchen_name='Uptown Test Kitchen',
                    total_revenue=Decimal('32500.00'),
                    booking_count=88,
                ),
            ],
            average_booking_value=Decimal('275.15'),
            revenue_forecast=[TimeSeriesData(date=today, value=Decimal('16000.00'))],
            payment_methods_breakdown=[
                PaymentMethodBreakdown(method='card', percentage=72.5),
                PaymentMethodBreakdown(method='ach', percentage=19.4),
            ],
        )
        self._growth = PlatformGrowthMetrics(
            user_signups=[TimeSeriesData(date=yesterday, value=80), TimeSeriesData(date=today, value=95)],
            host_signups=[TimeSeriesData(date=yesterday, value=12), TimeSeriesData(date=today, value=14)],
            conversion_rate=[TimeSeriesData(date=today, value=5.8)],
            acquisition_channels=[
                GrowthChannelBreakdown(channel='referrals', signups=60, conversion_rate=7.2),
                GrowthChannelBreakdown(channel='paid', signups=48, conversion_rate=4.1),
            ],
        )
        self._moderation = ModerationQueueMetrics(
            pending=14,
            in_review=6,
            escalated=2,
            sla_breaches=1,
            average_review_time_hours=3.4,
            moderation_trend=[TimeSeriesData(date=today, value=14)],
        )
        self._performance = AdminPerformanceMetrics(
            total_resolved=42,
            backlog=5,
            productivity_trend=[TimeSeriesData(date=today, value=42)],
            team=[
                AdminTeamMemberPerformance(
                    admin_id=uuid4(),
                    admin_name='Amelia Reviewer',
                    resolved_cases=24,
                    average_resolution_time_hours=2.5,
                    quality_score=96.0,
                ),
                AdminTeamMemberPerformance(
                    admin_id=uuid4(),
                    admin_name='Noah Specialist',
                    resolved_cases=18,
                    average_resolution_time_hours=3.1,
                    quality_score=93.5,
                ),
            ],
        )
        self._financial = FinancialHealthMetrics(
            total_revenue=Decimal('125000.00'),
            net_revenue=Decimal('88000.00'),
            operational_expenses=Decimal('32000.00'),
            gross_margin=68.5,
            ebitda_margin=42.1,
            cash_on_hand=Decimal('540000.00'),
            burn_rate=Decimal('28000.00'),
            runway_months=18.2,
            revenue_trend=[TimeSeriesData(date=today, value=Decimal('15250.25'))],
            expense_trend=[TimeSeriesData(date=today, value=Decimal('8200.00'))],
        )
        self._regions = [
            RegionPerformance(region='Austin', bookings=240, revenue=Decimal('24500.00'), growth_rate=6.2),
            RegionPerformance(region='Seattle', bookings=180, revenue=Decimal('19800.00'), growth_rate=4.5),
        ]

    async def get_platform_overview(self) -> PlatformOverviewMetrics:
        return self._overview

    async def get_platform_revenue(self, timeframe) -> RevenueAnalytics:  # noqa: ANN001
        return self._revenue

    async def get_platform_growth(self) -> PlatformGrowthMetrics:
        return self._growth

    async def get_platform_regions(self) -> list[RegionPerformance]:
        return self._regions

    async def get_moderation_metrics(self) -> ModerationQueueMetrics:
        return self._moderation

    async def get_admin_performance(self) -> AdminPerformanceMetrics:
        return self._performance

    async def get_financial_health(self) -> FinancialHealthMetrics:
        return self._financial


@dataclass
class StubAuthUser:
    id: UUID
    email: str = 'analytics-admin@example.com'
    is_admin: bool = True
    is_suspended: bool = False


@pytest.fixture
async def analytics_app():
    stub_service = StubAnalyticsDashboardService()
    stub_user = StubAuthUser(id=uuid4())

    app = FastAPI()
    app.include_router(analytics_router)

    async def _get_admin():
        return stub_user

    async def _get_service():
        return stub_service

    app.dependency_overrides[auth_get_current_admin] = _get_admin
    app.dependency_overrides[get_dashboard_service] = _get_service

    yield app

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_platform_analytics_endpoints(analytics_app) -> None:  # type: ignore[annotation-unchecked]
    transport = ASGITransport(app=analytics_app)
    async with AsyncClient(transport=transport, base_url='http://testserver') as client:
        overview = await client.get('/api/v1/analytics/platform/overview')
        assert overview.status_code == 200
        overview_payload = overview.json()
        assert overview_payload['total_users'] == 1200
        assert overview_payload['bookings_trend'][0]['value'] == 180

        revenue = await client.get('/api/v1/analytics/platform/revenue')
        assert revenue.status_code == 200
        revenue_payload = revenue.json()
        assert revenue_payload['average_booking_value'] == '275.15'
        assert len(revenue_payload['revenue_by_kitchen']) == 2

        growth = await client.get('/api/v1/analytics/platform/growth')
        assert growth.status_code == 200
        growth_payload = growth.json()
        assert growth_payload['acquisition_channels'][0]['channel'] == 'referrals'

        regions = await client.get('/api/v1/analytics/platform/regions')
        assert regions.status_code == 200
        assert regions.json()[0]['region'] == 'Austin'

        moderation = await client.get('/api/v1/analytics/admin/moderation')
        assert moderation.status_code == 200
        assert moderation.json()['pending'] == 14

        performance = await client.get('/api/v1/analytics/admin/performance')
        assert performance.status_code == 200
        performance_payload = performance.json()
        assert performance_payload['total_resolved'] == 42
        assert len(performance_payload['team']) == 2

        financial = await client.get('/api/v1/analytics/admin/financial')
        assert financial.status_code == 200
        financial_payload = financial.json()
        assert financial_payload['runway_months'] == 18.2
