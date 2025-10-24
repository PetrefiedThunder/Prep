"""FastAPI router exposing analytics dashboards backed by async PostgreSQL."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from prep.admin.analytics_service import AnalyticsService, StaticAnalyticsRepository
from prep.models.admin import BookingStatistics, HostPerformanceMetrics, PlatformOverview, RevenueAnalytics

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

_DEFAULT_SERVICE = AnalyticsService(repository=StaticAnalyticsRepository())


async def get_analytics_service() -> AnalyticsService:
    """FastAPI dependency providing the analytics service instance."""

    return _DEFAULT_SERVICE


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
    start_date: Annotated[datetime | None, Query(description="Filter bookings created after this timestamp")] = None,
    end_date: Annotated[datetime | None, Query(description="Filter bookings created before this timestamp")] = None,
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> BookingStatistics:
    """Return booking analytics for an optional date range."""

    return await analytics_service.get_booking_statistics(start_date=start_date, end_date=end_date)


@router.get("/revenue", response_model=RevenueAnalytics)
async def get_revenue_analytics(
    start_date: Annotated[datetime | None, Query(description="Include revenue generated after this timestamp")] = None,
    end_date: Annotated[datetime | None, Query(description="Include revenue generated before this timestamp")] = None,
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
