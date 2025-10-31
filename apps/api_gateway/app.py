from __future__ import annotations

from fastapi import FastAPI

from .routes.city import router as city_router


def create_app() -> FastAPI:
    """Construct the FastAPI application."""
    app = FastAPI(title="Prep API", version="0.1.0")
    app.include_router(city_router, prefix="/city", tags=["city"])
    return app


app = create_app()
