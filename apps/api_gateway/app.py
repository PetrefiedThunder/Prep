"""Minimal FastAPI application used for API gateway tests."""

from __future__ import annotations

from fastapi import FastAPI

from apps.api_gateway.routes.city import router as city_router


def create_app() -> FastAPI:
    """Return a lightweight FastAPI app wired with the city fee routes."""

    app = FastAPI(title="Prep API Gateway (tests)")
    app.include_router(city_router)
from .routes.city import router as city_router


def create_app() -> FastAPI:
    """Construct the FastAPI application."""
    app = FastAPI(title="Prep API", version="0.1.0")
    app.include_router(city_router, prefix="/city", tags=["city"])
    return app


app = create_app()
