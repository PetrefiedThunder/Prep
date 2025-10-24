"""Admin dashboard and certification API utilities."""

from .api import AdminDashboardAPI, get_admin_dashboard_api, router
from .certification_api import (
    CertificationVerificationAPI,
    certification_router,
    get_certification_verification_api,
)
from fastapi import APIRouter

from .api import AdminDashboardAPI, get_admin_dashboard_api, router as dashboard_router
from .certification_api import router as certification_router

router = APIRouter()
router.include_router(dashboard_router)
router.include_router(certification_router)

__all__ = [
    "AdminDashboardAPI",
    "CertificationVerificationAPI",
    "certification_router",
    "get_admin_dashboard_api",
    "get_certification_verification_api",
    "router",
]
