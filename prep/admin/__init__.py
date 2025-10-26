"""Admin dashboard and certification API utilities."""

from __future__ import annotations

import os

from fastapi import APIRouter

from .analytics_api import get_analytics_service, router as analytics_router
from .api import router as legacy_dashboard_router
from .dashboard_db_api import router as database_dashboard_router

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

if os.getenv("PREP_USE_DB_ADMIN_ROUTER") == "1":
    router.include_router(database_dashboard_router)
else:
    router.include_router(legacy_dashboard_router)

router.include_router(certification_router)
router.include_router(analytics_router)

__all__ = [
    "CertificationVerificationAPI",
    "certification_router",
    "database_dashboard_router",
    "get_analytics_service",
    "get_certification_verification_api",
    "legacy_dashboard_router",
    "router",
]
