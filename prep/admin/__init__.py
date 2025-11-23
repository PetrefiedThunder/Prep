"""Admin dashboard and certification API utilities."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter

__all__ = [
    "CertificationVerificationAPI",
    "analytics_router",
    "certification_router",
    "database_dashboard_router",
    "get_analytics_service",
    "get_certification_verification_api",
    "legacy_dashboard_router",
    "router",
]


def __getattr__(name: str) -> Any:  # pragma: no cover - thin convenience wrappers
    if name == "get_analytics_service":
        from .analytics_api import get_analytics_service as attr

        return attr
    if name == "analytics_router":
        from .analytics_api import router as attr

        return attr
    if name == "legacy_dashboard_router":
        from .api import router as attr

        return attr
    if name == "database_dashboard_router":
        from .dashboard_db_api import router as attr

        return attr
    if name in {
        "CertificationVerificationAPI",
        "certification_router",
        "get_certification_verification_api",
    }:
        try:
            from .certification_api import (
                CertificationVerificationAPI as cert_api,
                certification_router as cert_router,
                get_certification_verification_api as cert_getter,
            )
        except Exception as exc:  # pragma: no cover - degraded environments
            cert_router = APIRouter()

            def cert_getter(exc: Exception = exc) -> None:
                raise RuntimeError("Certification API module is unavailable") from exc

            cert_api = None  # type: ignore[assignment]

        if name == "CertificationVerificationAPI":
            return cert_api
        if name == "certification_router":
            return cert_router
        return cert_getter
    if name == "router":
        router = APIRouter()

        if os.getenv("PREP_USE_DB_ADMIN_ROUTER") == "1":
            router.include_router(__getattr__("database_dashboard_router"))
        else:
            router.include_router(__getattr__("legacy_dashboard_router"))

        router.include_router(__getattr__("certification_router"))
        router.include_router(__getattr__("analytics_router"))
        return router
    raise AttributeError(name)
