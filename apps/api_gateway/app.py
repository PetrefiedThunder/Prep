"""Minimal FastAPI application used for API gateway tests."""

from __future__ import annotations

from fastapi import FastAPI

from apps.api_gateway.routes.city import router as city_router


def create_app() -> FastAPI:
    """Return a lightweight FastAPI app wired with the city fee routes."""

    app = FastAPI(title="Prep API Gateway (tests)")
    app.include_router(city_router)
    return app


app = create_app()
