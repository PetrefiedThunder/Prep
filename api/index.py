"""Vercel-compatible FastAPI entrypoint that exposes the Prep API surface."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.compliance_service.main import app as compliance_app
from prep.admin.api import router as admin_router
from prep.analytics.advanced_api import router as advanced_analytics_router
from prep.analytics.dashboard_api import router as analytics_router
from prep.cities.api import router as cities_router
from prep.kitchen_cam.api import router as kitchen_cam_router
from prep.matching.api import router as matching_router
from prep.mobile.api import router as mobile_router
from prep.platform.api import router as platform_router
from prep.payments.api import router as payments_router
from prep.ratings.api import router as ratings_router
from prep.reviews.api import router as reviews_router


def _build_router() -> APIRouter:
    """Aggregate the project's routers into a single API surface."""

    router = APIRouter()
    router.include_router(platform_router)
    router.include_router(mobile_router)
    router.include_router(admin_router)
    router.include_router(analytics_router)
    router.include_router(advanced_analytics_router)
    router.include_router(matching_router)
    router.include_router(reviews_router)
    router.include_router(ratings_router)
    router.include_router(cities_router)
    router.include_router(kitchen_cam_router)
    router.include_router(payments_router)
    return router


def create_app() -> FastAPI:
    """Instantiate the FastAPI application used by Vercel."""

    app = FastAPI(title="Prep API Gateway", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    app.include_router(_build_router())

    @app.get("/healthz", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        """Lightweight readiness probe for hosting platforms."""

        return {"status": "ok"}

    app.mount("/compliance", compliance_app)

    return app


app = create_app()
