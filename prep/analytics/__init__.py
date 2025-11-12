"""Analytics dashboard API and utilities."""

from .advanced_api import get_advanced_analytics_service, router as advanced_router
from .dashboard_api import (
    AnalyticsDashboardService,
    get_current_admin,
    get_current_user,
    get_dashboard_service,
    router,
)
from .realtime_engine import AnalyticsRepository, Booking, RealtimeAnalyticsEngine, Review

__all__ = [
    "AnalyticsDashboardService",
    "get_dashboard_service",
    "get_current_admin",
    "get_current_user",
    "router",
    "advanced_router",
    "get_advanced_analytics_service",
    "AnalyticsRepository",
    "Booking",
    "RealtimeAnalyticsEngine",
    "Review",
]
