"""City fee endpoints exposed via the API gateway."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from importlib import import_module
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Response

from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeSchedule,
    FeeValidationResult,
    validate_fee_schedule,
)

router = APIRouter(prefix="/city", tags=["city-fees"])

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
    body = json.dumps(payload)
    return Response(
        content=body,
        media_type="application/json",
        headers={"ETag": f'"{etag}"'},
    )
