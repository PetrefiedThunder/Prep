"""FastAPI router exposing San Francisco compliance endpoints."""

from __future__ import annotations

from calendar import monthrange
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .models import (
    BookingFlowRecord,
    BookingValidationRequest,
    CityETLRunRecord,
    FireComplianceRecord,
    HealthPermitRecord,
    HostComplianceStatus,
    HostKitchenRecord,
    MetricsSnapshot,
    TaxBreakdown,
    TaxCalculationRequest,
    TaxReportRecord,
    WasteComplianceRecord,
    ZoningVerificationRecord,
)
from .service import SFComplianceService, service

router = APIRouter(prefix="/api/sf", tags=["San Francisco Compliance"])
booking_router = APIRouter(tags=["San Francisco Compliance"])


async def get_service() -> SFComplianceService:
    return service


def _period_to_dates(period: str) -> tuple[datetime, datetime]:
    try:
        year_str, quarter_str = period.split("-")
        year = int(year_str)
        quarter = int(quarter_str.removeprefix("Q"))
        if quarter not in {1, 2, 3, 4}:
            raise ValueError
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="period must be formatted as YYYY-Q#, e.g. 2025-Q1",
        ) from exc

    start_month = (quarter - 1) * 3 + 1
    start = datetime(year, start_month, 1, tzinfo=UTC)
    end_month = start_month + 2
    last_day = monthrange(year, end_month)[1]
    end = datetime(year, end_month, last_day, tzinfo=UTC)
    return start, end


@router.post(
    "/host-onboard", response_model=HostComplianceStatus, status_code=status.HTTP_201_CREATED
)
async def onboard_host(
    payload: HostKitchenRecord,
    svc: SFComplianceService = Depends(get_service),
) -> HostComplianceStatus:
    """Register or update an SF host and evaluate compliance."""

    return await svc.upsert_host(payload)


@router.get("/host/{host_id}/compliance-status", response_model=HostComplianceStatus)
async def get_compliance_status(
    host_id: UUID,
    svc: SFComplianceService = Depends(get_service),
) -> HostComplianceStatus:
    """Return detailed compliance checklist for a host."""

    try:
        return await svc.get_host_status(host_id)
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Host not found") from exc


@router.get("/zoning/check", response_model=ZoningVerificationRecord)
async def zoning_check(
    address: Annotated[str, Query(min_length=3)],
    business_type: Annotated[str, Query(alias="business_type", min_length=3)] = "cooking_kitchen",
    zoning_use_district: Annotated[str | None, Query(alias="zoning", min_length=1)] = None,
    host_id: UUID | None = None,
    svc: SFComplianceService = Depends(get_service),
) -> ZoningVerificationRecord:
    """Perform a zoning lookup for the provided address."""

    target_host = host_id or UUID(int=0)
    return await svc.perform_zoning_check(
        host_id=target_host,
        address=address,
        zoning_use_district=zoning_use_district,
        business_type=business_type,
    )


@router.post("/tax/calculate", response_model=TaxBreakdown)
async def calculate_tax(
    payload: TaxCalculationRequest,
    svc: SFComplianceService = Depends(get_service),
) -> TaxBreakdown:
    """Calculate San Francisco taxes for a booking."""

    return await svc.calculate_tax(payload)


@router.post("/tax/report", response_model=TaxReportRecord, status_code=status.HTTP_201_CREATED)
async def upsert_tax_report(
    payload: TaxReportRecord,
    svc: SFComplianceService = Depends(get_service),
) -> TaxReportRecord:
    """Store a quarterly SF tax report summary."""

    return await svc.store_tax_report(payload)


@router.get("/tax/report", response_model=TaxReportRecord)
async def get_tax_report(
    period: Annotated[str, Query(min_length=6)],
    jurisdiction: str = "San Francisco",
    svc: SFComplianceService = Depends(get_service),
) -> TaxReportRecord:
    """Fetch a previously prepared SF tax report for the requested period."""

    period_start, period_end = _period_to_dates(period)
    try:
        return await svc.get_tax_report(
            period_start=period_start.date(),
            period_end=period_end.date(),
            jurisdiction=jurisdiction,
        )
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tax report not found") from exc


@router.post("/health/validate", response_model=HealthPermitRecord)
async def validate_health_permit(
    payload: HealthPermitRecord,
    svc: SFComplianceService = Depends(get_service),
) -> HealthPermitRecord:
    """Store the results of an SF health permit validation."""

    return await svc.upsert_health_permit(payload)


@router.get("/health/permit/{permit_number}/status", response_model=HealthPermitRecord)
async def get_health_permit(
    permit_number: str,
    svc: SFComplianceService = Depends(get_service),
) -> HealthPermitRecord:
    """Retrieve health permit status."""

    try:
        return await svc.get_health_permit(permit_number)
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Permit not found") from exc


@router.post("/fire/verify", response_model=FireComplianceRecord)
async def verify_fire_compliance(
    payload: FireComplianceRecord,
    svc: SFComplianceService = Depends(get_service),
) -> FireComplianceRecord:
    """Record fire suppression verification details."""

    return await svc.upsert_fire_record(payload)


@router.get("/fire/status/{host_id}", response_model=FireComplianceRecord)
async def get_fire_status(
    host_id: UUID,
    svc: SFComplianceService = Depends(get_service),
) -> FireComplianceRecord:
    try:
        return await svc.get_fire_record(host_id)
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Fire record not found") from exc


@router.post("/waste/verify", response_model=WasteComplianceRecord)
async def verify_waste(
    payload: WasteComplianceRecord,
    svc: SFComplianceService = Depends(get_service),
) -> WasteComplianceRecord:
    """Record grease trap compliance verification."""

    return await svc.upsert_waste_record(payload)


@router.get("/waste/status/{host_id}", response_model=WasteComplianceRecord)
async def get_waste_status(
    host_id: UUID,
    svc: SFComplianceService = Depends(get_service),
) -> WasteComplianceRecord:
    try:
        return await svc.get_waste_record(host_id)
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Waste record not found") from exc


@router.post("/etl/runs", response_model=CityETLRunRecord, status_code=status.HTTP_201_CREATED)
async def record_etl_run(
    payload: CityETLRunRecord,
    svc: SFComplianceService = Depends(get_service),
) -> CityETLRunRecord:
    """Record the results of a San Francisco ETL run."""

    return await svc.record_etl_run(payload)


@router.get("/etl/runs", response_model=list[CityETLRunRecord])
async def list_etl_runs(
    limit: Annotated[int, Query(gt=0, le=50)] = 10,
    svc: SFComplianceService = Depends(get_service),
) -> list[CityETLRunRecord]:
    """Return the most recent SF ETL run metadata."""

    runs = await svc.recent_etl_runs(limit=limit)
    return list(runs)


@router.get("/metrics", response_model=MetricsSnapshot)
async def get_metrics(
    svc: SFComplianceService = Depends(get_service),
) -> MetricsSnapshot:
    """Expose an aggregated metrics snapshot for monitoring."""

    return await svc.metrics()


@booking_router.post("/booking/validateForSF", response_model=BookingFlowRecord)
async def validate_booking(
    payload: BookingValidationRequest,
    svc: SFComplianceService = Depends(get_service),
) -> BookingFlowRecord:
    """Internal hook used by the booking flow to evaluate SF compliance."""

    return await svc.validate_booking(payload)


__all__ = [
    "booking_router",
    "router",
]
