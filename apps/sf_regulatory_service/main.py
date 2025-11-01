"""FastAPI application for the San Francisco regulatory service."""

from __future__ import annotations

import time
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse

from . import metrics
from .config import load_config
from .database import get_session, init_db
from .schemas import (
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    ComplianceResponse,
    FireVerificationRequest,
    FireVerificationResponse,
    HealthPermitValidationRequest,
    HealthPermitValidationResponse,
    HostStatusResponse,
    SFHostProfilePayload,
    WasteVerificationRequest,
    WasteVerificationResponse,
    ZoningCheckResponse,
)
from .services import SFRegulatoryService


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="San Francisco Regulatory Service", version="1.0.0")

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

    @app.get("/sf/requirements", response_model=dict, tags=["configuration"])
    def get_requirements() -> dict:
        return load_config()

    @app.post("/sf/host/onboard", response_model=ComplianceResponse, tags=["hosts"])
    def onboard_host(
        payload: SFHostProfilePayload,
        service: SFRegulatoryService = Depends(lambda session=Depends(get_session): SFRegulatoryService(session)),
    ) -> ComplianceResponse:
        return service.onboard_host(payload)

    @app.get(
        "/sf/host/{host_kitchen_id}/status",
        response_model=HostStatusResponse,
        tags=["hosts"],
    )
    def host_status(
        host_kitchen_id: str,
        service: SFRegulatoryService = Depends(lambda session=Depends(get_session): SFRegulatoryService(session)),
    ) -> HostStatusResponse:
        try:
            return service.get_host_status(host_kitchen_id)
        except ValueError as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        "/sf/zoning/check",
        response_model=ZoningCheckResponse,
        tags=["zoning"],
    )
    def zoning_check(
        address: str = Query(...),
        business_type: str = Query("kitchen"),
        zoning_use_district: Optional[str] = Query(None, alias="district"),
        service: SFRegulatoryService = Depends(lambda session=Depends(get_session): SFRegulatoryService(session)),
    ) -> ZoningCheckResponse:
        _ = business_type
        return service.check_zoning(address, zoning_use_district)

    @app.post(
        "/sf/health/validate",
        response_model=HealthPermitValidationResponse,
        tags=["health"],
    )
    def health_validate(
        request: HealthPermitValidationRequest,
        service: SFRegulatoryService = Depends(lambda session=Depends(get_session): SFRegulatoryService(session)),
    ) -> HealthPermitValidationResponse:
        return service.validate_health_permit(request)

    @app.post(
        "/sf/fire/verify",
        response_model=FireVerificationResponse,
        tags=["fire"],
    )
    def fire_verify(
        request: FireVerificationRequest,
        service: SFRegulatoryService = Depends(lambda session=Depends(get_session): SFRegulatoryService(session)),
    ) -> FireVerificationResponse:
        return service.verify_fire(request)

    @app.post(
        "/sf/waste/verify",
        response_model=WasteVerificationResponse,
        tags=["waste"],
    )
    def waste_verify(
        request: WasteVerificationRequest,
        service: SFRegulatoryService = Depends(lambda session=Depends(get_session): SFRegulatoryService(session)),
    ) -> WasteVerificationResponse:
        return service.verify_waste(request)

    @app.post(
        "/sf/compliance/check",
        response_model=ComplianceCheckResponse,
        tags=["compliance"],
    )
    def compliance_check(
        request: ComplianceCheckRequest,
        service: SFRegulatoryService = Depends(lambda session=Depends(get_session): SFRegulatoryService(session)),
    ) -> ComplianceCheckResponse:
        try:
            return service.check_booking(request)
        except ValueError as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


app = create_app()
