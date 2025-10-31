"""Vercel-compatible FastAPI entrypoint that exposes the Prep API surface."""

from __future__ import annotations

from collections.abc import Iterable
from importlib import import_module

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:  # pragma: no cover - fallback for stubbed services with syntax issues
    from apps.compliance_service.main import app as compliance_app
except (SyntaxError, ImportError):  # pragma: no cover
    compliance_app = FastAPI(title="Compliance Service (unavailable)")
try:  # pragma: no cover - inventory service may have incompatible stubs
    from apps.inventory_service.main import app as inventory_app
except (SyntaxError, ImportError):  # pragma: no cover
    inventory_app = FastAPI(title="Inventory Service (unavailable)")


def _load_router(module_path: str, attr: str = "router") -> APIRouter:
    """Load an APIRouter from the provided module path, returning an empty router when unavailable."""

    try:
        module = import_module(module_path)
    except Exception:  # pragma: no cover - optional router modules may have missing deps
        return APIRouter()

    router_obj = getattr(module, attr, None)
    return router_obj if isinstance(router_obj, APIRouter) else APIRouter()


ledger_router = _load_router("prep.accounting", "ledger_router")
platform_router = _load_router("prep.platform.api")
mobile_router = _load_router("prep.mobile.api")
admin_router = _load_router("prep.admin.api")
analytics_router = _load_router("prep.analytics.dashboard_api")
host_metrics_router = _load_router("prep.analytics.host_metrics_api")
advanced_analytics_router = _load_router("prep.analytics.advanced_api")
matching_router = _load_router("prep.matching.api")
reviews_router = _load_router("prep.reviews.api")
ratings_router = _load_router("prep.ratings.api")
cities_router = _load_router("prep.cities.api")
kitchen_cam_router = _load_router("prep.kitchen_cam.api")
payments_router = _load_router("prep.payments.api")
pos_router = _load_router("prep.pos.api")
test_data_router = _load_router("prep.test_data")
space_optimizer_router = _load_router("api.space_optimizer")
integrations_router = _load_router("prep.integrations.api")
monitoring_router = _load_router("prep.monitoring.api")
verification_tasks_router = _load_router("prep.verification_tasks.api")
square_kds_router = _load_router("api.webhooks.square_kds")
logistics_router = _load_router("prep.logistics.api")
deliveries_router = _load_router("prep.api.deliveries")
orders_router = _load_router("prep.api.orders")

try:  # pragma: no cover - observability hooks are optional in tests
    from modules.observability import DEFAULT_TARGETED_ROUTES, configure_fastapi_tracing
except Exception:  # pragma: no cover
    DEFAULT_TARGETED_ROUTES: tuple[str, ...] = ()

    def configure_fastapi_tracing(app: FastAPI, targeted_routes: Iterable[str] | None = None) -> None:  # type: ignore[override]
        return None

try:  # pragma: no cover - integration runtime hooks may pull optional deps
    from prep.integrations.runtime import configure_integration_event_consumers
except Exception:  # pragma: no cover

    def configure_integration_event_consumers(app: FastAPI) -> None:  # type: ignore[override]
        return None

from api.routes.city_fees import router as city_fees_router
from api.routes.diff import router as city_diff_router


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
    router.include_router(city_fees_router, prefix="/city", tags=["city"])
    router.include_router(city_diff_router)
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

    app.include_router(_build_router())
    try:  # pragma: no cover - integrations may require external services
        configure_integration_event_consumers(app)
    except RuntimeError:
        pass

    @app.get("/healthz", tags=["health"])
    async def healthcheck() -> dict[str, str]:
        """Lightweight readiness probe for hosting platforms."""

        return {"status": "ok"}

    app.mount("/compliance", compliance_app)
    app.mount("/inventory", inventory_app)

    return app


app = create_app()
