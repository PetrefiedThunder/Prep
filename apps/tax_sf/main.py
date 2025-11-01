"""FastAPI application for the San Francisco tax service."""

from __future__ import annotations

import time

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from apps.sf_regulatory_service import metrics
from apps.sf_regulatory_service.database import get_session, init_db

from .schemas import TaxCalculateRequest, TaxCalculateResponse, TaxReportResponse
from .services import TaxService


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="San Francisco Tax Service", version="1.0.0")

    @app.middleware("http")
    async def metrics_middleware(request, call_next):  # type: ignore[override]
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        metrics.http_server_latency_seconds.labels(route=request.url.path).observe(elapsed)
        return response

    @app.get("/health", tags=["meta"])
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
    def metrics_endpoint() -> PlainTextResponse:
        return PlainTextResponse(metrics.generate_latest(), media_type=metrics.CONTENT_TYPE_LATEST)

    @app.post("/sf/tax/calculate", response_model=TaxCalculateResponse, tags=["tax"])
    def calculate_tax(
        request: TaxCalculateRequest,
        service: TaxService = Depends(lambda session=Depends(get_session): TaxService(session)),
    ) -> TaxCalculateResponse:
        try:
            return service.calculate(request)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/sf/tax/report", response_model=TaxReportResponse, tags=["tax"])
    def tax_report(
        period: str,
        service: TaxService = Depends(lambda session=Depends(get_session): TaxService(session)),
    ) -> TaxReportResponse:
        return service.generate_report(period)

    return app


app = create_app()
