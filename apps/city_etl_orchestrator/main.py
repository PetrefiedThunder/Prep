"""FastAPI application exposing the City ETL orchestrator."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from apps.sf_regulatory_service.database import init_db

from . import metrics
from .config import load_settings
from .orchestrator import CityEtlOrchestrator


def create_app() -> FastAPI:
    """Instantiate the FastAPI application and background scheduler."""

    init_db()
    settings = load_settings()
    orchestrator = CityEtlOrchestrator(interval_seconds=settings.interval_seconds)

    app = FastAPI(title="City ETL Orchestrator", version="1.0.0")

    @app.on_event("startup")
    async def _start() -> None:  # pragma: no cover - exercised in integration tests
        orchestrator.start()

    @app.on_event("shutdown")
    async def _shutdown() -> None:  # pragma: no cover - exercised in integration tests
        orchestrator.stop()

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, Optional[str]]:
        last_run = orchestrator.last_run
        last_success = orchestrator.last_success_at
        now = datetime.utcnow()
        freshness_budget = settings.freshness_slo_seconds
        freshness_age = (
            (now - last_success).total_seconds() if last_success else None
        )
        status = "starting"
        if freshness_age is not None:
            status = "ok" if freshness_age <= freshness_budget else "degraded"

        response: dict[str, Optional[str]] = {
            "status": status,
            "city": orchestrator.city,
            "last_run_status": last_run.status if last_run else None,
            "last_run_finished_at": last_run.finished_at.isoformat() if last_run else None,
            "last_success_at": last_success.isoformat() if last_success else None,
        }
        return response

    @app.post("/runs/trigger", tags=["runs"])
    def trigger_run() -> dict[str, str]:
        try:
            result = orchestrator.run_once()
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        return {
            "city": result.city,
            "status": result.status,
            "started_at": result.started_at.isoformat(),
            "finished_at": result.finished_at.isoformat(),
        }

    @app.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
    def metrics_endpoint() -> PlainTextResponse:
        metrics.update_freshness_gauge(orchestrator.city, orchestrator.last_success_at)
        return PlainTextResponse(metrics.generate_latest(), media_type=metrics.CONTENT_TYPE_LATEST)

    return app


app = create_app()
