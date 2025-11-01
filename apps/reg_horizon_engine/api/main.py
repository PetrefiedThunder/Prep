"""FastAPI application exposing the Regulatory Horizon Engine."""
from __future__ import annotations

from fastapi import FastAPI

from ..config import get_settings
from . import routes


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Regulatory Horizon Engine", version="0.1.0")

    @app.get("/healthz")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.service_name}

    @app.get("/readyz")
    async def ready() -> dict[str, str]:
        return {"status": "ready"}

    app.include_router(routes.router, prefix="/api")
    return app


app = create_app()
