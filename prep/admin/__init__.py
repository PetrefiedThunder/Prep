"""Admin dashboard and certification API utilities."""

from __future__ import annotations

import os

from fastapi import APIRouter

from .api import AdminDashboardAPI, get_admin_dashboard_api, router as legacy_dashboard_router
from .certification_api import (
    CertificationVerificationAPI,
    certification_router as legacy_certification_router,
    get_certification_verification_api,
)
from .dashboard_db_api import router as database_dashboard_router

router = APIRouter()

if os.getenv("PREP_USE_DB_ADMIN_ROUTER") == "1":
    router.include_router(database_dashboard_router)
else:
    router.include_router(legacy_dashboard_router)

certification_router = legacy_certification_router
router.include_router(certification_router)

__all__ = [
    "AdminDashboardAPI",
    "CertificationVerificationAPI",
    "certification_router",
    "database_dashboard_router",
    "get_admin_dashboard_api",
    "get_certification_verification_api",
    "router",
]
