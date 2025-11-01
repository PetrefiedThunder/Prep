"""Backward-compatible shim importing the city fee router."""

from __future__ import annotations

from api.routes.city_fees import router

__all__ = ["router"]
from fastapi import APIRouter, Header, HTTPException, Response
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from api.routes._city_utils import ingestor_module_for, normalize_city
from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeSchedule,
    FeeValidationResult,
    validate_fee_schedule,
)

router = APIRouter(prefix="/city", tags=["city-fees"])
router = APIRouter()


def _load_schedule(city_norm: str) -> FeeSchedule:
    mod = _ingestor_module_for(city_norm)
    if not hasattr(mod, "make_fee_schedule"):
        raise HTTPException(
            status_code=500,
            detail=f"Ingestor missing make_fee_schedule() for '{city_norm}'",
        )
    schedule = mod.make_fee_schedule()
    if not isinstance(schedule, FeeSchedule):
        raise HTTPException(status_code=500, detail="Invalid fee schedule payload")
    return schedule


def _etag_for_schedule(schedule: FeeSchedule) -> str:
    canonical = {
        "jurisdiction": schedule.jurisdiction,
        "paperwork": sorted(schedule.paperwork),
        "fees": sorted(
            [item.dict() for item in schedule.fees],
            key=lambda data: (
                data.get("name", ""),
                data.get("kind", ""),
                data.get("cadence", ""),
                data.get("unit", ""),
            ),
        ),
    }
    payload = json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@router.get("/{city}/fees")
def get_city_fees(city: str) -> dict[str, Any]:
    city_norm = _normalize(city)
    try:
        schedule = _load_schedule(city_norm)
    except KeyError as exc:  # pragma: no cover - FastAPI handles conversion
        raise HTTPException(status_code=404, detail=f"Unsupported city '{city}'") from exc

    validation: FeeValidationResult = validate_fee_schedule(schedule)
    return {
        "jurisdiction": schedule.jurisdiction,
        "paperwork": list(schedule.paperwork),
        "fees": [item.dict() for item in schedule.fees],
        "totals": {
            "one_time_cents": schedule.total_one_time_cents,
            "recurring_annualized_cents": schedule.total_recurring_annualized_cents,
            "incremental_fee_count": validation.incremental_fee_count,
        },
        "validation": {
            "is_valid": validation.is_valid,
            "issues": validation.issues,
        },
    }


@router.get("/{city}/fees/summary")
def get_city_fees_summary(
    city: str,
    if_none_match: str | None = Header(default=None),
):
    """Return a lightweight fee schedule summary with cache validation."""

    city_norm = _normalize(city)
    try:
        schedule = _load_schedule(city_norm)
    except KeyError as exc:  # pragma: no cover - FastAPI handles conversion
        raise HTTPException(status_code=404, detail=f"Unsupported city '{city}'") from exc

    etag = _etag_for_schedule(schedule)
    if if_none_match and if_none_match.strip('"') == etag:
        return Response(status_code=304, headers={"ETag": f'"{etag}"'})

    validation: FeeValidationResult = validate_fee_schedule(schedule)
    payload = {
        "jurisdiction": schedule.jurisdiction,
@router.get("/{city}/fees")
def get_city_fees(city: str) -> Dict[str, Any]:
    """Return the normalized fee schedule for the provided city."""

    try:
        city_norm = normalize_city(city)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unsupported city '{city}'") from exc
    try:
        module = ingestor_module_for(city_norm)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unsupported city '{city}'") from exc

    if not hasattr(module, "make_fee_schedule"):
        raise HTTPException(
            status_code=500, detail=f"Ingestor missing make_fee_schedule() for '{city_norm}'"
        )

    schedule: FeeSchedule = module.make_fee_schedule()
    validation: FeeValidationResult = validate_fee_schedule(schedule)

