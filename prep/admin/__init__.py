"""Prep admin package exports."""

from __future__ import annotations

from fastapi import APIRouter

from .api import router as admin_router
from .analytics_api import router as analytics_router

router = APIRouter()
router.include_router(admin_router)
router.include_router(analytics_router)

__all__ = ["router"]
