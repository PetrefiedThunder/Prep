"""Vercel-compatible FastAPI entrypoint that exposes the Prep API surface."""

from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI
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
from prep.auth.dependencies import enforce_allowlists, require_active_session
from prep.auth.rbac import RBACMiddleware
from prep.platform.api import auth_router, router as platform_router
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
from prep.settings import get_settings


def _build_router() -> APIRouter:
    """Aggregate the project's routers into a single API surface."""

    router = APIRouter(dependencies=[Depends(enforce_allowlists), Depends(require_active_session)])
    router.include_router(ledger_router)
    router.include_router(auth_router)
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

    settings = get_settings()
    app = FastAPI(title="Prep API Gateway", version="1.0.0")

    configure_fastapi_tracing(app, targeted_routes=DEFAULT_TARGETED_ROUTES)

    app.add_middleware(RBACMiddleware, settings=settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    app.include_router(_build_router())
    configure_integration_event_consumers(app)

    @app.get("/healthz", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        """Lightweight readiness probe for hosting platforms."""

        return {"status": "ok"}

    app.mount("/compliance", compliance_app)
    app.mount("/inventory", inventory_app)

    return app


app = create_app()
