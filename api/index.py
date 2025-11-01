"""FastAPI application factory for the consolidated Prep API gateway."""

from __future__ import annotations

from importlib import import_module
from typing import Iterable

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware


def _load_router(module_path: str, attr: str = "router") -> APIRouter:
    """Import *module_path* and return the attribute named *attr* if it is an APIRouter.

    Missing modules or attributes are treated as optional so the gateway can boot even
    when a downstream service has been archived.
    """

    try:
        module = import_module(module_path)
    except Exception:  # pragma: no cover - optional routers may be absent
        return APIRouter()

    router_obj = getattr(module, attr, None)
    return router_obj if isinstance(router_obj, APIRouter) else APIRouter()


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


def create_app() -> FastAPI:
    """Construct the FastAPI application used by the API gateway."""

    app = FastAPI(title="Prep API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for module_path in OPTIONAL_ROUTERS:
        router = _load_router(module_path)
        if router.routes:
            app.include_router(router)

    @app.get("/healthz", include_in_schema=False)
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

__all__ = ["app", "create_app"]
