"""FastAPI application factory for the consolidated Prep API gateway."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from libs.safe_import import safe_import
from prep.auth.dependencies import enforce_allowlists, require_active_session

logger = logging.getLogger(__name__)


def _load_router(module_path: str, attr: str = "router") -> APIRouter:
    """Import *module_path* and return the attribute named *attr* if it is an APIRouter.

    Missing modules or attributes are treated as optional so the gateway can boot even
    when a downstream service has been archived.
    """
    module = safe_import(module_path, optional=True)
    if module is None:
        logger.info("Optional router module %s not available, using empty router", module_path)
        return APIRouter()

    router_obj = getattr(module, attr, None)
    if router_obj is None:
        logger.warning("Module %s has no attribute '%s', using empty router", module_path, attr)
        return APIRouter()

    if not isinstance(router_obj, APIRouter):
        logger.warning(
            "Module %s.%s is not an APIRouter (got %s), using empty router",
            module_path,
            attr,
            type(router_obj).__name__,
        )
        return APIRouter()

    return router_obj


OPTIONAL_ROUTERS: Iterable[str] = (
    "api.routes.city_fees",
    "api.routes.diff",
    "api.city.requirements",
    "api.routes.debug",
    "api.webhooks.square_kds",
    "prep.analytics.dashboard_api",
    "prep.analytics.host_metrics_api",
    "prep.matching.api",
    "prep.payments.api",
    "prep.ratings.api",
    "prep.reviews.api",
    "prep.verification_tasks.api",
)


def _build_router(*, include_full: bool = True) -> APIRouter:
    """Aggregate the project's routers into a single API surface."""

    router = APIRouter(dependencies=[Depends(enforce_allowlists), Depends(require_active_session)])

    if include_full:
        router.include_router(_load_router("prep.ledger.api", "ledger_router"))
        router.include_router(_load_router("prep.auth.api", "auth_router"))
        router.include_router(_load_router("prep.platform.api", "platform_router"))
        router.include_router(_load_router("prep.mobile.api", "mobile_router"))
        router.include_router(_load_router("prep.admin.api", "admin_router"))
        router.include_router(_load_router("prep.analytics.api", "analytics_router"))
        router.include_router(_load_router("prep.analytics.host_metrics_api", "host_metrics_router"))
        router.include_router(_load_router("prep.analytics.advanced_api", "advanced_analytics_router"))
        router.include_router(_load_router("prep.matching.api", "matching_router"))
        router.include_router(_load_router("prep.reviews.api", "reviews_router"))
        router.include_router(_load_router("prep.ratings.api", "ratings_router"))
        router.include_router(_load_router("prep.cities.api", "cities_router"))
        router.include_router(_load_router("prep.kitchen_cam.api", "kitchen_cam_router"))
        router.include_router(_load_router("prep.payments.api", "payments_router"))
        router.include_router(_load_router("prep.pos.api", "pos_router"))
        router.include_router(_load_router("prep.test_data.api", "test_data_router"))
        router.include_router(_load_router("prep.space_optimizer.api", "space_optimizer_router"))
        router.include_router(_load_router("prep.integrations.api", "integrations_router"))
        router.include_router(_load_router("prep.monitoring.api", "monitoring_router"))
        router.include_router(_load_router("prep.verification_tasks.api", "verification_tasks_router"))
        router.include_router(_load_router("api.webhooks.square_kds", "square_kds_router"))
        router.include_router(_load_router("prep.logistics.api", "logistics_router"))
        router.include_router(_load_router("prep.deliveries.api", "deliveries_router"))
        router.include_router(_load_router("prep.orders.api", "orders_router"))

    router.include_router(_load_router("api.routes.debug", "debug_router"))
    router.include_router(_load_router("api.routes.city_fees", "city_fees_router"), prefix="/city", tags=["city"])
    router.include_router(_load_router("api.routes.diff", "city_diff_router"))
    router.include_router(_load_router("api.city.requirements", "city_requirements_router"))

    return router


def create_app(*, include_full_router: bool = True, include_legacy_mounts: bool = True) -> FastAPI:
    """Instantiate the FastAPI application for our default containerized deployment."""

    settings = get_settings()
    app = FastAPI(title="Prep API Gateway", version="1.0.0")

    if settings.environment.lower() == "staging":
        from prep.database import get_session_factory

        app.state.db = get_session_factory()
        app.middleware("http")(audit_logger)

    app.add_middleware(
        RBACMiddleware,
        settings=settings,
        route_roles={
            "/api/v1/admin": {"operator_admin"},
            "/api/v1/analytics": {"operator_admin", "support_analyst"},
            "/api/v1/matching": {"operator_admin", "support_analyst"},
            "/api/v1/cities": {"operator_admin", "city_reviewer"},
            "/api/v1/platform": set(RBAC_ROLES),
        },
        exempt_paths=(
            "/healthz",
            "/docs",
            "/openapi.json",
            "/api/v1/platform/users/register",
            "/api/v1/platform/auth/login",
            "/api/v1/platform/auth/token",
            "/api/v1/platform/auth/refresh",
        ),
    )

    configure_fastapi_tracing(app, targeted_routes=DEFAULT_TARGETED_ROUTES)

    # SECURITY FIX: Use specific origins instead of wildcard to prevent CSRF attacks
    # Configure allowed origins from environment variable
    import os

    allowed_origins = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000"
    ).split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    )

    for module_path in OPTIONAL_ROUTERS:
        router = _load_router(module_path)
        if router.routes:
            app.include_router(router)
    security_dependencies = [Depends(enforce_client_allowlist), Depends(enforce_active_session)]
    api_router = _build_router(include_full=include_full_router)
    app.include_router(api_router, dependencies=security_dependencies)

    try:  # pragma: no cover - integrations may require external services
        configure_integration_event_consumers(app)
    except RuntimeError:
        pass

    @app.get("/healthz", include_in_schema=False)
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

__all__ = ["app", "create_app"]
