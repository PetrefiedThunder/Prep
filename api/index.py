"""Vercel-compatible FastAPI entrypoint that exposes the Prep API surface."""

from __future__ import annotations

import ipaddress
from datetime import UTC, datetime
from typing import Sequence

import jwt
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request, status
from fastapi import APIRouter, Depends, FastAPI
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
from apps.compliance_service.main import app as compliance_app
from prep.accounting import ledger_router
from apps.inventory_service.main import app as inventory_app
from prep.admin.api import router as admin_router
from prep.analytics.advanced_api import router as advanced_analytics_router
from prep.analytics.dashboard_api import router as analytics_router
from prep.analytics.host_metrics_api import router as host_metrics_router
from apps.api_gateway.routes.city import router as city_fees_router
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
from prep.auth.rbac import RBACMiddleware, RBAC_ROLES
from prep.cache import RedisProtocol, get_redis
from prep.settings import Settings, get_settings


def _ip_in_allowlist(ip: str, allowlist: Sequence[str]) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        return False

    for entry in allowlist:
        value = entry.strip()
        if not value:
            continue
        if value == "*":
            return True
        try:
            network = ipaddress.ip_network(value, strict=False)
        except ValueError:
            if value == ip:
                return True
        else:
            if ip_obj in network:
                return True
    return False


async def enforce_client_allowlist(
    request: Request,
    settings: Settings = Depends(get_settings),
    device_id: str | None = Header(default=None, alias="X-Device-ID"),
) -> None:
    client_host = request.client.host if request.client else None
    if settings.auth_ip_allowlist:
        if not client_host or not _ip_in_allowlist(client_host, settings.auth_ip_allowlist):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Request IP address is not allowed",
            )
    if settings.auth_device_allowlist:
        if device_id is None or device_id not in settings.auth_device_allowlist:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device is not authorized",
            )


async def enforce_active_session(
    request: Request,
    cache: RedisProtocol = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> None:
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.lower().startswith("bearer "):
        return

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=("HS256",))
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token expired",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
        )

    exp = payload.get("exp")
    if exp is not None:
        expires_at = datetime.fromtimestamp(int(exp), tz=UTC)
        if expires_at < datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session token expired",
            )

    cache_key = f"session:{token}"
    cached = await cache.get(cache_key)
    if cached is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is no longer active",
        )
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
    router.include_router(city_fees_router, prefix="/city", tags=["city"])
    router.include_router(city_diff_router)
    router.include_router(city_fees_router)
    return router


def create_app() -> FastAPI:
    """Instantiate the FastAPI application used by Vercel."""

    settings = get_settings()
    app = FastAPI(title="Prep API Gateway", version="1.0.0")

    settings = get_settings()
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

    app.add_middleware(RBACMiddleware, settings=settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    security_dependencies = [Depends(enforce_client_allowlist), Depends(enforce_active_session)]
    app.include_router(_build_router(), dependencies=security_dependencies)
    configure_integration_event_consumers(app)
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
