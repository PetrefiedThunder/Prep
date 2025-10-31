from __future__ import annotations

from functools import lru_cache
from importlib import import_module
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeSchedule,
    FeeValidationResult,
    validate_fee_schedule,
)

router = APIRouter()

_CANON = {
    "san francisco": "san_francisco",
    "sf": "san_francisco",
    "oakland": "oakland",
    "berkeley": "berkeley",
    "san jose": "san_jose",
    "sj": "san_jose",
    "palo alto": "palo_alto",
    "palo_alto": "palo_alto",
    "joshua tree": "joshua_tree",
    "joshua_tree": "joshua_tree",
}


def _normalize(city: str) -> str:
    key = city.strip().lower()
    return _CANON.get(key, key.replace("-", "_").replace(" ", "_"))


@lru_cache(maxsize=64)
def _ingestor_module_for(city_norm: str):
    mod_map = {
        "san_francisco": "data.ingestors.sf_dph",
        "oakland": "data.ingestors.oakland_dph",
        "berkeley": "data.ingestors.berkeley_dph",
        "san_jose": "data.ingestors.san_jose_dph",
        "palo_alto": "data.ingestors.palo_alto_dph",
        "joshua_tree": "data.ingestors.joshua_tree_dph",
    }
    path = mod_map.get(city_norm)
    if not path:
        raise KeyError(city_norm)
    return import_module(path)


@router.get("/{city}/fees")
def get_city_fees(city: str) -> Dict[str, Any]:
    """Return the normalized fee schedule for the provided city."""

    city_norm = _normalize(city)
    try:
        module = _ingestor_module_for(city_norm)
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
        "paperwork": schedule.paperwork,
        "fees": [fee.dict() for fee in schedule.fees],
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
