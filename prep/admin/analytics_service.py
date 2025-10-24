"""Analytics service and repository abstractions for admin dashboards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Iterable, Mapping, Protocol
from uuid import UUID

from prep.models.admin import (
    BookingStatistics,
    HostPerformanceMetrics,
    KitchenPerformanceSummary,
    PlatformOverview,
    RevenueAnalytics,
    TimeSeriesPoint,
)


class AnalyticsRepository(Protocol):
    """Protocol describing the analytics persistence interface."""

    async def fetch_host_metrics(self, host_id: UUID) -> HostPerformanceMetrics:
        """Return aggregated metrics for a specific host."""

    async def fetch_booking_statistics(
        self,
        *,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> BookingStatistics:
        """Return booking statistics for an optional date range."""

    async def fetch_revenue_analytics(
        self,
        *,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> RevenueAnalytics:
        """Return revenue analytics including trend data."""

    async def fetch_platform_overview(self) -> PlatformOverview:
        """Return a platform level overview."""


@dataclass(slots=True)
class AnalyticsService:
    """Orchestrates analytics queries for the FastAPI layer."""

    repository: AnalyticsRepository

    async def get_host_performance(self, host_id: UUID) -> HostPerformanceMetrics:
        return await self.repository.fetch_host_metrics(host_id)

    async def get_booking_statistics(
        self,
        *,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> BookingStatistics:
        return await self.repository.fetch_booking_statistics(start_date=start_date, end_date=end_date)

    async def get_revenue_analytics(
        self,
        *,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> RevenueAnalytics:
        return await self.repository.fetch_revenue_analytics(start_date=start_date, end_date=end_date)

    async def get_platform_overview(self) -> PlatformOverview:
        return await self.repository.fetch_platform_overview()


class PostgresAnalyticsRepository:
    """Analytics repository backed by an async PostgreSQL connection."""

    def __init__(self, connection: "AsyncPGConnection") -> None:
        self._connection = connection

    async def fetch_host_metrics(self, host_id: UUID) -> HostPerformanceMetrics:
        row = await self._connection.fetchrow(
            """
            WITH host_kitchens AS (
                SELECT k.id, k.name, k.is_active, k.host_id
                FROM kitchens AS k
                WHERE k.host_id = $1
            ),
            kitchen_stats AS (
                SELECT
                    b.kitchen_id,
                    COUNT(*) AS total_bookings,
                    COALESCE(SUM(b.total_amount), 0) AS revenue,
                    COALESCE(AVG(r.rating), 0) AS avg_rating
                FROM bookings AS b
                LEFT JOIN reviews AS r ON r.booking_id = b.id
                WHERE b.kitchen_id IN (SELECT id FROM host_kitchens)
                GROUP BY b.kitchen_id
            ),
            last_month_bookings AS (
                SELECT COUNT(*) AS bookings
                FROM bookings
                WHERE kitchen_id IN (SELECT id FROM host_kitchens)
                  AND started_at >= $2
            )
            SELECT
                h.id AS host_id,
                h.full_name AS host_name,
                COUNT(DISTINCT hk.id) AS kitchen_count,
                COUNT(DISTINCT hk.id) FILTER (WHERE hk.is_active) AS active_kitchen_count,
                COALESCE(SUM(ks.total_bookings), 0) AS total_bookings,
                COALESCE(SUM(ks.revenue), 0) AS total_revenue,
                COALESCE(AVG(ks.avg_rating), 0) AS average_rating,
                (SELECT bookings FROM last_month_bookings) AS bookings_last_30_days
            FROM hosts AS h
            LEFT JOIN host_kitchens AS hk ON hk.host_id = h.id
            LEFT JOIN kitchen_stats AS ks ON ks.kitchen_id = hk.id
            WHERE h.id = $1
            GROUP BY h.id, h.full_name
            """,
            host_id,
            datetime.now(tz=UTC) - timedelta(days=30),
        )

        if row is None:
            raise LookupError(f"Host {host_id} not found")

        kitchen_rows = await self._connection.fetch(
            """
            SELECT
                k.id AS kitchen_id,
                k.name AS kitchen_name,
                COALESCE(stats.total_bookings, 0) AS total_bookings,
                COALESCE(stats.revenue, 0) AS revenue,
                COALESCE(stats.avg_rating, 0) AS average_rating
            FROM kitchens AS k
            LEFT JOIN (
                SELECT
                    b.kitchen_id,
                    COUNT(*) AS total_bookings,
                    COALESCE(SUM(b.total_amount), 0) AS revenue,
                    COALESCE(AVG(r.rating), 0) AS avg_rating
                FROM bookings AS b
                LEFT JOIN reviews AS r ON r.booking_id = b.id
                WHERE b.kitchen_id IN (
                    SELECT id FROM kitchens WHERE host_id = $1
                )
                GROUP BY b.kitchen_id
            ) AS stats ON stats.kitchen_id = k.id
            WHERE k.host_id = $1
            ORDER BY stats.revenue DESC NULLS LAST
            LIMIT 5
            """,
            host_id,
        )

        return HostPerformanceMetrics(
            host_id=row["host_id"],
            host_name=row["host_name"],
            kitchen_count=row["kitchen_count"],
            active_kitchen_count=row["active_kitchen_count"],
            total_bookings=row["total_bookings"],
            total_revenue=Decimal(row["total_revenue"]),
            average_rating=float(row["average_rating"]),
            bookings_last_30_days=row["bookings_last_30_days"],
            top_kitchens=[
                KitchenPerformanceSummary(
                    kitchen_id=kitchen_row["kitchen_id"],
                    kitchen_name=kitchen_row["kitchen_name"],
                    total_bookings=kitchen_row["total_bookings"],
                    revenue=Decimal(kitchen_row["revenue"]),
                    average_rating=float(kitchen_row["average_rating"]),
                )
                for kitchen_row in kitchen_rows
            ],
        )

    async def fetch_booking_statistics(
        self,
        *,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> BookingStatistics:
        row = await self._connection.fetchrow(
            """
            SELECT
                COUNT(*) AS total_bookings,
                COUNT(*) FILTER (WHERE status = 'completed') AS completed_bookings,
                COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled_bookings,
                COUNT(*) FILTER (WHERE status = 'no_show') AS no_show_bookings,
                COALESCE(AVG(EXTRACT(EPOCH FROM (started_at - created_at)) / 3600.0), 0) AS average_lead_time_hours,
                COALESCE(AVG(total_amount), 0) AS average_booking_value
            FROM bookings
            WHERE ($1::timestamptz IS NULL OR created_at >= $1)
              AND ($2::timestamptz IS NULL OR created_at <= $2)
            """,
            start_date,
            end_date,
        )

        if row is None:
            return BookingStatistics(
                total_bookings=0,
                completed_bookings=0,
                cancelled_bookings=0,
                no_show_bookings=0,
                average_lead_time_hours=0.0,
                average_booking_value=Decimal("0"),
            )

        return BookingStatistics(
            total_bookings=row["total_bookings"],
            completed_bookings=row["completed_bookings"],
            cancelled_bookings=row["cancelled_bookings"],
            no_show_bookings=row["no_show_bookings"],
            average_lead_time_hours=float(row["average_lead_time_hours"]),
            average_booking_value=Decimal(row["average_booking_value"]),
        )

    async def fetch_revenue_analytics(
        self,
        *,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> RevenueAnalytics:
        summary = await self._connection.fetchrow(
            """
            SELECT
                COALESCE(SUM(total_amount), 0) AS total_revenue,
                COALESCE(
                    SUM(total_amount) FILTER (
                        WHERE date_trunc('month', created_at) = date_trunc('month', CURRENT_DATE)
                    ),
                    0
                ) AS revenue_this_month
            FROM bookings
            WHERE status = 'completed'
              AND ($1::timestamptz IS NULL OR created_at >= $1)
              AND ($2::timestamptz IS NULL OR created_at <= $2)
            """,
            start_date,
            end_date,
        )

        if summary is None:
            summary = {"total_revenue": Decimal("0"), "revenue_this_month": Decimal("0")}

        previous_month = await self._connection.fetchrow(
            """
            SELECT COALESCE(SUM(total_amount), 0) AS revenue
            FROM bookings
            WHERE status = 'completed'
              AND date_trunc('month', created_at) = date_trunc('month', CURRENT_DATE - INTERVAL '1 month')
            """
        )

        if previous_month is None:
            previous_month = {"revenue": Decimal("0")}

        trend_rows = await self._connection.fetch(
            """
            SELECT
                date_trunc('week', created_at) AS period,
                COALESCE(SUM(total_amount), 0) AS revenue
            FROM bookings
            WHERE status = 'completed'
              AND ($1::timestamptz IS NULL OR created_at >= $1)
              AND ($2::timestamptz IS NULL OR created_at <= $2)
            GROUP BY date_trunc('week', created_at)
            ORDER BY period ASC
            """,
            start_date,
            end_date,
        )

        top_host_rows = await self._connection.fetch(
            """
            SELECT
                h.id AS host_id,
                h.full_name AS host_name,
                COUNT(DISTINCT k.id) AS kitchen_count,
                COUNT(DISTINCT k.id) FILTER (WHERE k.is_active) AS active_kitchen_count,
                COUNT(b.id) AS total_bookings,
                COALESCE(SUM(b.total_amount), 0) AS total_revenue,
                COALESCE(AVG(r.rating), 0) AS average_rating
            FROM hosts AS h
            JOIN kitchens AS k ON k.host_id = h.id
            LEFT JOIN bookings AS b ON b.kitchen_id = k.id AND b.status = 'completed'
            LEFT JOIN reviews AS r ON r.booking_id = b.id
            WHERE ($1::timestamptz IS NULL OR b.created_at >= $1)
              AND ($2::timestamptz IS NULL OR b.created_at <= $2)
            GROUP BY h.id, h.full_name
            ORDER BY total_revenue DESC
            LIMIT 5
            """,
            start_date,
            end_date,
        )

        total_revenue = Decimal(summary["total_revenue"])
        revenue_this_month = Decimal(summary["revenue_this_month"])
        previous_month_revenue = Decimal(previous_month["revenue"])
        growth = (
            float(((revenue_this_month - previous_month_revenue) / previous_month_revenue) * 100)
            if previous_month_revenue
            else float(100 if revenue_this_month else 0)
        )

        return RevenueAnalytics(
            total_revenue=total_revenue,
            revenue_this_month=revenue_this_month,
            month_over_month_growth=growth,
            revenue_trend=[
                TimeSeriesPoint(period=row["period"], value=Decimal(row["revenue"])) for row in trend_rows
            ],
            top_hosts=[
                HostPerformanceMetrics(
                    host_id=row["host_id"],
                    host_name=row["host_name"],
                    kitchen_count=row["kitchen_count"],
                    active_kitchen_count=row["active_kitchen_count"],
                    total_bookings=row["total_bookings"],
                    total_revenue=Decimal(row["total_revenue"]),
                    average_rating=float(row["average_rating"]),
                    bookings_last_30_days=0,
                    top_kitchens=[],
                )
                for row in top_host_rows
            ],
        )

    async def fetch_platform_overview(self) -> PlatformOverview:
        row = await self._connection.fetchrow(
            """
            SELECT
                (SELECT COUNT(*) FROM kitchens) AS total_kitchens,
                (SELECT COUNT(*) FROM kitchens WHERE is_active) AS active_kitchens,
                (SELECT COUNT(*) FROM bookings) AS total_bookings,
                (SELECT COALESCE(SUM(total_amount), 0) FROM bookings WHERE status = 'completed' AND created_at >= $1)
                    AS revenue_this_month,
                (SELECT COALESCE(AVG(rating), 0) FROM reviews) AS user_satisfaction,
                (SELECT COUNT(*) FROM users WHERE created_at >= $2) AS new_users_this_week
            """,
            datetime.now(tz=UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            datetime.now(tz=UTC) - timedelta(days=7),
        )

        if row is None:
            row = {
                "total_kitchens": 0,
                "active_kitchens": 0,
                "total_bookings": 0,
                "revenue_this_month": Decimal("0"),
                "user_satisfaction": 0.0,
                "new_users_this_week": 0,
            }

        return PlatformOverview(
            total_kitchens=row["total_kitchens"],
            active_kitchens=row["active_kitchens"],
            total_bookings=row["total_bookings"],
            revenue_this_month=Decimal(row["revenue_this_month"]),
            conversion_rate=0.0,
            user_satisfaction=float(row["user_satisfaction"]),
            new_users_this_week=row["new_users_this_week"],
        )


class StaticAnalyticsRepository:
    """In-memory analytics repository used for tests and local development."""

    def __init__(self) -> None:
        now = datetime(2025, 1, 15, tzinfo=UTC)
        self._host_metrics = HostPerformanceMetrics(
            host_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            host_name="Sample Host",
            kitchen_count=2,
            active_kitchen_count=2,
            total_bookings=128,
            total_revenue=Decimal("48750.00"),
            average_rating=4.6,
            bookings_last_30_days=18,
            top_kitchens=[
                KitchenPerformanceSummary(
                    kitchen_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                    kitchen_name="Sunset Loft Kitchen",
                    total_bookings=74,
                    revenue=Decimal("31250.00"),
                    average_rating=4.8,
                ),
                KitchenPerformanceSummary(
                    kitchen_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
                    kitchen_name="Harborview Test Kitchen",
                    total_bookings=54,
                    revenue=Decimal("17500.00"),
                    average_rating=4.3,
                ),
            ],
        )
        self._booking_stats = BookingStatistics(
            total_bookings=320,
            completed_bookings=280,
            cancelled_bookings=28,
            no_show_bookings=12,
            average_lead_time_hours=36.5,
            average_booking_value=Decimal("285.00"),
        )
        self._revenue = RevenueAnalytics(
            total_revenue=Decimal("182500.00"),
            revenue_this_month=Decimal("22500.00"),
            month_over_month_growth=12.5,
            revenue_trend=[
                TimeSeriesPoint(period=now - timedelta(weeks=3), value=Decimal("42000.00")),
                TimeSeriesPoint(period=now - timedelta(weeks=2), value=Decimal("46500.00")),
                TimeSeriesPoint(period=now - timedelta(weeks=1), value=Decimal("51800.00")),
                TimeSeriesPoint(period=now, value=Decimal("42000.00")),
            ],
            top_hosts=[self._host_metrics],
        )
        self._overview = PlatformOverview(
            total_kitchens=84,
            active_kitchens=76,
            total_bookings=5400,
            revenue_this_month=Decimal("22500.00"),
            conversion_rate=0.18,
            user_satisfaction=4.5,
            new_users_this_week=64,
        )

    async def fetch_host_metrics(self, host_id: UUID) -> HostPerformanceMetrics:
        if host_id != self._host_metrics.host_id:
            raise LookupError(f"Host {host_id} not found")
        return self._host_metrics

    async def fetch_booking_statistics(
        self,
        *,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> BookingStatistics:
        return self._booking_stats

    async def fetch_revenue_analytics(
        self,
        *,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> RevenueAnalytics:
        return self._revenue

    async def fetch_platform_overview(self) -> PlatformOverview:
        return self._overview


class AsyncPGConnection(Protocol):
    """Subset of asyncpg connection methods used by the repository."""

    async def fetchrow(self, query: str, *args) -> Mapping[str, object] | None:
        ...

    async def fetch(self, query: str, *args) -> Iterable[Mapping[str, object]]:
        ...
