from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Iterable, Mapping
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from prep.admin.analytics_api import get_analytics_service, router as analytics_router
from prep.admin.analytics_service import AnalyticsService, PostgresAnalyticsRepository
from prep.models.admin import (
    BookingStatistics,
    HostPerformanceMetrics,
    KitchenPerformanceSummary,
    PlatformOverview,
    RevenueAnalytics,
    TimeSeriesPoint,
)


class FakeAnalyticsRepository:
    def __init__(self) -> None:
        self.host_metrics = HostPerformanceMetrics(
            host_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            host_name="Test Host",
            kitchen_count=3,
            active_kitchen_count=2,
            total_bookings=150,
            total_revenue=Decimal("54000.00"),
            average_rating=4.5,
            bookings_last_30_days=22,
            top_kitchens=[
                KitchenPerformanceSummary(
                    kitchen_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                    kitchen_name="Kitchen One",
                    total_bookings=80,
                    revenue=Decimal("32000.00"),
                    average_rating=4.7,
                )
            ],
        )
        self.booking_stats = BookingStatistics(
            total_bookings=400,
            completed_bookings=360,
            cancelled_bookings=25,
            no_show_bookings=15,
            average_lead_time_hours=42.0,
            average_booking_value=Decimal("300.00"),
        )
        self.revenue = RevenueAnalytics(
            total_revenue=Decimal("250000.00"),
            revenue_this_month=Decimal("28000.00"),
            month_over_month_growth=15.0,
            revenue_trend=[
                TimeSeriesPoint(period=datetime(2025, 1, 1, tzinfo=UTC), value=Decimal("20000.00")),
                TimeSeriesPoint(period=datetime(2025, 1, 8, tzinfo=UTC), value=Decimal("22000.00")),
            ],
            top_hosts=[
                HostPerformanceMetrics(
                    host_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
                    host_name="Leaderboard Host",
                    kitchen_count=2,
                    active_kitchen_count=2,
                    total_bookings=190,
                    total_revenue=Decimal("70000.00"),
                    average_rating=4.8,
                    bookings_last_30_days=30,
                    top_kitchens=[],
                )
            ],
        )
        self.overview = PlatformOverview(
            total_kitchens=120,
            active_kitchens=95,
            total_bookings=6200,
            revenue_this_month=Decimal("28000.00"),
            conversion_rate=0.2,
            user_satisfaction=4.6,
            new_users_this_week=80,
        )

    async def fetch_host_metrics(self, host_id: UUID) -> HostPerformanceMetrics:
        if host_id != self.host_metrics.host_id:
            raise LookupError("Host not found")
        return self.host_metrics

    async def fetch_booking_statistics(
        self,
        *,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> BookingStatistics:
        return self.booking_stats

    async def fetch_revenue_analytics(
        self,
        *,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> RevenueAnalytics:
        return self.revenue

    async def fetch_platform_overview(self) -> PlatformOverview:
        return self.overview


class RecordingConnection:
    def __init__(
        self,
        *,
        fetchrow_responses: Iterable[Mapping[str, object] | None],
        fetch_responses: Iterable[Iterable[Mapping[str, object]]],
    ) -> None:
        self._fetchrow_iter = iter(fetchrow_responses)
        self._fetch_iter = iter(fetch_responses)
        self.queries: list[tuple[str, tuple[object, ...]]] = []

    async def fetchrow(self, query: str, *args) -> Mapping[str, object] | None:
        self.queries.append((query.strip(), args))
        return next(self._fetchrow_iter, None)

    async def fetch(self, query: str, *args) -> Iterable[Mapping[str, object]]:
        self.queries.append((query.strip(), args))
        return list(next(self._fetch_iter, []))


def test_service_delegates_to_repository() -> None:
    repository = FakeAnalyticsRepository()
    service = AnalyticsService(repository=repository)

    async def run() -> None:
        host_metrics = await service.get_host_performance(repository.host_metrics.host_id)
        booking_stats = await service.get_booking_statistics(start_date=None, end_date=None)
        revenue = await service.get_revenue_analytics(start_date=None, end_date=None)
        overview = await service.get_platform_overview()

        assert host_metrics.host_name == "Test Host"
        assert booking_stats.total_bookings == 400
        assert revenue.total_revenue == Decimal("250000.00")
        assert overview.total_kitchens == 120

    asyncio.run(run())


def test_postgres_repository_shapes_results() -> None:
    host_row = {
        "host_id": UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        "host_name": "Test Host",
        "kitchen_count": 2,
        "active_kitchen_count": 2,
        "total_bookings": 100,
        "total_revenue": Decimal("40000.00"),
        "average_rating": 4.5,
        "bookings_last_30_days": 10,
    }
    kitchen_series = [
        {
            "kitchen_id": UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            "kitchen_name": "Kitchen",
            "total_bookings": 50,
            "revenue": Decimal("20000.00"),
            "average_rating": 4.7,
        }
    ]
    connection = RecordingConnection(
        fetchrow_responses=[host_row],
        fetch_responses=[kitchen_series],
    )

    repository = PostgresAnalyticsRepository(connection)
    async def run() -> None:
        host_metrics = await repository.fetch_host_metrics(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))

        assert host_metrics.total_revenue == Decimal("40000.00")
        assert connection.queries  # ensure queries executed

    asyncio.run(run())


def test_fastapi_router_uses_service_dependency() -> None:
    repository = FakeAnalyticsRepository()
    service = AnalyticsService(repository)

    app = FastAPI()
    app.include_router(analytics_router)
    app.dependency_overrides[get_analytics_service] = lambda: service

    client = TestClient(app)
    host_id = str(repository.host_metrics.host_id)

    host_response = client.get(f"/api/v1/analytics/hosts/{host_id}")
    assert host_response.status_code == 200
    assert host_response.json()["host_name"] == "Test Host"

    bookings_response = client.get("/api/v1/analytics/bookings")
    assert bookings_response.status_code == 200
    assert bookings_response.json()["total_bookings"] == 400

    revenue_response = client.get("/api/v1/analytics/revenue")
    assert revenue_response.status_code == 200
    assert revenue_response.json()["total_revenue"] == "250000.00"

    overview_response = client.get("/api/v1/analytics/overview")
    assert overview_response.status_code == 200
    assert overview_response.json()["total_kitchens"] == 120
