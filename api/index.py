"""Vercel-compatible FastAPI entrypoint that exposes the Prep API surface."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from apps.compliance_service.main import app as compliance_app
from prep.accounting import ledger_router
from apps.inventory_service.main import app as inventory_app
from prep.admin.api import router as admin_router
from prep.analytics.advanced_api import router as advanced_analytics_router
from prep.analytics.dashboard_api import router as analytics_router
from prep.analytics.host_metrics_api import router as host_metrics_router
from prep.cities.api import router as cities_router
from prep.api.deliveries import router as deliveries_router
from prep.api.orders import router as orders_router
from prep.kitchen_cam.api import router as kitchen_cam_router
from prep.integrations.api import router as integrations_router
from prep.matching.api import router as matching_router
from prep.mobile.api import router as mobile_router
from prep.platform.api import router as platform_router
from prep.payments.api import router as payments_router
from prep.ratings.api import router as ratings_router
from prep.reviews.api import router as reviews_router
from prep.test_data import router as test_data_router

from api.space_optimizer import router as space_optimizer_router
from prep.verification_tasks.api import router as verification_tasks_router
from modules.observability import DEFAULT_TARGETED_ROUTES, configure_fastapi_tracing
from api.webhooks.square_kds import router as square_kds_router
from prep.logistics.api import router as logistics_router
from prep.monitoring.api import router as monitoring_router
from prep.integrations.runtime import configure_integration_event_consumers
from prep.pos.api import router as pos_router
from prep.api.middleware import IdempotencyMiddleware


def _build_router() -> APIRouter:
    """Aggregate the project's routers into a single API surface."""

    router = APIRouter()
    router.include_router(ledger_router)
    router.include_router(platform_router)
    router.include_router(mobile_router)
    router.include_router(admin_router)
    router.include_router(analytics_router)
    router.include_router(host_metrics_router)
    router.include_router(advanced_analytics_router)
    router.include_router(matching_router)
    router.include_router(reviews_router)
    router.include_router(ratings_router)
    router.include_router(cities_router)
    router.include_router(kitchen_cam_router)
    router.include_router(payments_router)
    router.include_router(pos_router)
    router.include_router(test_data_router)
    router.include_router(space_optimizer_router)
    router.include_router(integrations_router)
    router.include_router(monitoring_router)
    router.include_router(verification_tasks_router)
    router.include_router(square_kds_router)
    router.include_router(logistics_router)
    router.include_router(deliveries_router)
    router.include_router(orders_router)
    return router


def create_app() -> FastAPI:
    """Instantiate the FastAPI application used by Vercel."""

    app = FastAPI(title="Prep API Gateway", version="1.0.0")

    configure_fastapi_tracing(app, targeted_routes=DEFAULT_TARGETED_ROUTES)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )
    app.add_middleware(IdempotencyMiddleware)

    app.include_router(_build_router())
    configure_integration_event_consumers(app)

    API_VERSION = "v1"
    sunset_date = "Wed, 01 Jan 2025 00:00:00 GMT"

    @app.middleware("http")
    async def _apply_version_headers(request: Request, call_next):
        response: Response = await call_next(request)
        response.headers.setdefault("X-API-Version", API_VERSION)
        if not request.url.path.startswith(f"/api/{API_VERSION}"):
            response.headers.setdefault("Deprecation", f"version={API_VERSION}-1")
            response.headers.setdefault("Sunset", sunset_date)
        return response

    @app.get("/v1", tags=["meta"])
    async def version_guidance() -> dict[str, str]:
        """Communicate stable API versioning guidance to integrators."""

        return {
            "version": API_VERSION,
            "status": "stable",
            "guidance": "All new integrations should target /api/v1 endpoints. Unversioned paths will sunset soon.",
            "sunset": sunset_date,
        }

    @app.get("/healthz", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        """Lightweight readiness probe for hosting platforms."""

        return {"status": "ok"}

    app.mount("/compliance", compliance_app)
    app.mount("/inventory", inventory_app)

    return app


app = create_app()
