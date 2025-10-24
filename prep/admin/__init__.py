"""Admin dashboard API package exports."""

from __future__ import annotations

from fastapi import APIRouter

from .analytics_api import get_analytics_service, router as analytics_router
from .api import AdminDashboardAPI, get_admin_dashboard_api, router as dashboard_router

try:  # pragma: no cover - degraded environments without certification API
    from .certification_api import (
        CertificationVerificationAPI,
        certification_router as _certification_router,
        get_certification_verification_api,
    )
except SyntaxError as exc:  # pragma: no cover - legacy modules with syntax errors
    certification_router = APIRouter()

    def get_certification_verification_api() -> None:
        raise RuntimeError("Certification API module is unavailable") from exc

    CertificationVerificationAPI = None  # type: ignore[assignment]
else:
    certification_router = _certification_router

router = APIRouter()
router.include_router(dashboard_router)
router.include_router(certification_router)
router.include_router(analytics_router)

__all__ = [
    "AdminDashboardAPI",
    "CertificationVerificationAPI",
    "certification_router",
    "get_admin_dashboard_api",
    "get_analytics_service",
    "get_certification_verification_api",
    "router",
]
from prep.admin.api import router

__all__ = ["router"]
