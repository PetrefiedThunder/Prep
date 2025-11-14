"""FastAPI router exposing analytics dashboards backed by async PostgreSQL."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from prep.admin.analytics_service import (
    AnalyticsRepository,
    AnalyticsService,
    PostgresAnalyticsRepository,
    StaticAnalyticsRepository,
)
from prep.models.admin import (
    BookingStatistics,
    HostPerformanceMetrics,
    PlatformOverview,
    RevenueAnalytics,
)
from prep.settings import get_settings

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

_STATIC_SERVICE = AnalyticsService(repository=StaticAnalyticsRepository())
_postgres_service: AnalyticsService | None = None
_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()
_service_lock = asyncio.Lock()


class _PoolBackedAnalyticsRepository(AnalyticsRepository):
    """Wrap :class:`PostgresAnalyticsRepository` to use a connection pool."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def fetch_host_metrics(self, host_id: UUID) -> HostPerformanceMetrics:
        async with self._pool.acquire() as connection:
            repository = PostgresAnalyticsRepository(connection)
            return await repository.fetch_host_metrics(host_id)

    async def fetch_booking_statistics(
        self,
        *,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> BookingStatistics:
        async with self._pool.acquire() as connection:
            repository = PostgresAnalyticsRepository(connection)
            return await repository.fetch_booking_statistics(
                start_date=start_date, end_date=end_date
            )

    async def fetch_revenue_analytics(
        self,
        *,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> RevenueAnalytics:
        async with self._pool.acquire() as connection:
            repository = PostgresAnalyticsRepository(connection)
            return await repository.fetch_revenue_analytics(
                start_date=start_date, end_date=end_date
            )

    async def fetch_platform_overview(self) -> PlatformOverview:
        async with self._pool.acquire() as connection:
            repository = PostgresAnalyticsRepository(connection)
            return await repository.fetch_platform_overview()


def _should_use_fixtures() -> bool:
    """Return ``True`` when fixture-backed repositories are enabled."""

    # ``get_settings`` is cached, so callers must clear the cache if they mutate env vars.
    return get_settings().use_fixtures


def _normalize_database_url(url: str) -> str:
    """Convert SQLAlchemy style URLs to asyncpg compatible DSNs."""

    return url.replace("+asyncpg", "", 1)


async def _get_pool() -> asyncpg.Pool:
    """Return a cached asyncpg connection pool."""

    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                settings = get_settings()
                dsn = _normalize_database_url(str(settings.database_url))
                _pool = await asyncpg.create_pool(dsn=dsn)
    return _pool


async def _get_postgres_service() -> AnalyticsService:
    """Return an :class:`AnalyticsService` backed by PostgreSQL."""

    global _postgres_service
    if _postgres_service is None:
        async with _service_lock:
            if _postgres_service is None:
                pool = await _get_pool()
                repository = _PoolBackedAnalyticsRepository(pool)
                _postgres_service = AnalyticsService(repository=repository)
    return _postgres_service


async def get_analytics_service() -> AnalyticsService:
    """FastAPI dependency providing the analytics service instance."""

    if _should_use_fixtures():
        return _STATIC_SERVICE
    return await _get_postgres_service()


@router.on_event("shutdown")
async def _shutdown_analytics_resources() -> None:
    """Release pooled connections when the application stops."""

    global _pool, _postgres_service
    if _pool is not None:
        await _pool.close()
    _pool = None
    _postgres_service = None


@router.get("/hosts/{host_id}", response_model=HostPerformanceMetrics)
async def get_host_dashboard(
    host_id: UUID,
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> HostPerformanceMetrics:
    """Return analytics for a specific host."""

    try:
        return await analytics_service.get_host_performance(host_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/bookings", response_model=BookingStatistics)
async def get_booking_statistics(
    start_date: Annotated[
        datetime | None, Query(description="Filter bookings created after this timestamp")
    ] = None,
    end_date: Annotated[
        datetime | None, Query(description="Filter bookings created before this timestamp")
    ] = None,
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> BookingStatistics:
    """Return booking analytics for an optional date range."""

    return await analytics_service.get_booking_statistics(start_date=start_date, end_date=end_date)


@router.get("/revenue", response_model=RevenueAnalytics)
async def get_revenue_analytics(
    start_date: Annotated[
        datetime | None, Query(description="Include revenue generated after this timestamp")
    ] = None,
    end_date: Annotated[
        datetime | None, Query(description="Include revenue generated before this timestamp")
    ] = None,
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> RevenueAnalytics:
    """Return revenue analytics including trend data."""

    return await analytics_service.get_revenue_analytics(start_date=start_date, end_date=end_date)


@router.get("/overview", response_model=PlatformOverview)
async def get_platform_overview(
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> PlatformOverview:
    """Return a platform level overview for dashboards."""

    return await analytics_service.get_platform_overview()


__all__ = [
    "get_analytics_service",
    "router",
]
