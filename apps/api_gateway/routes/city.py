"""City fee schedule API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from api.routes._city_utils import ingestor_module_for, normalize_city
from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeSchedule,
    FeeValidationResult,
    validate_fee_schedule,
)

router = APIRouter()


@router.get("/{city}/fees")
def get_city_fees(city: str) -> dict[str, Any]:
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
