"""City fee endpoints exposed via the API gateway."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Response

from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeItem,
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


_FEE_SCHEDULES: dict[str, FeeSchedule] = {
    "san_francisco": FeeSchedule(
        jurisdiction="san_francisco",
        paperwork=("Application Form A-FOOD", "Plan Review Checklist PRC-12"),
        fees=(
            FeeItem(name="Food Facility Plan Review", amount_cents=45000, kind="one_time"),
            FeeItem(
                name="Annual Health Permit",
                amount_cents=98000,
                kind="recurring",
                cadence="annual",
            ),
            FeeItem(
                name="Reinspection Fee",
                amount_cents=30000,
                kind="incremental",
                unit="per_reinspection",
                incremental=True,
            ),
        ),
    ),
    "oakland": FeeSchedule(
        jurisdiction="oakland",
        paperwork=("Environmental Health Application", "Menu Worksheet"),
        fees=(
            FeeItem(name="Plan Review", amount_cents=38000, kind="one_time"),
            FeeItem(
                name="Annual Health Permit",
                amount_cents=82000,
                kind="recurring",
                cadence="annual",
            ),
        ),
    ),
    "berkeley": FeeSchedule(
        jurisdiction="berkeley",
        paperwork=("Retail Food Application", "Floor Plan Set"),
        fees=(
            FeeItem(name="Plan Check", amount_cents=42000, kind="one_time"),
            FeeItem(
                name="Retail Food License",
                amount_cents=90000,
                kind="recurring",
                cadence="annual",
            ),
        ),
    ),
    "san_jose": FeeSchedule(
        jurisdiction="san_jose",
        paperwork=("Santa Clara Food Permit Application", "Equipment Schedule"),
        fees=(
            FeeItem(name="Plan Review", amount_cents=40000, kind="one_time"),
            FeeItem(
                name="Operating Permit",
                amount_cents=76000,
                kind="recurring",
                cadence="annual",
            ),
        ),
    ),
    "palo_alto": FeeSchedule(
        jurisdiction="palo_alto",
        paperwork=("Santa Clara Health Application", "Menu Submission"),
        fees=(
            FeeItem(name="Plan Review", amount_cents=36000, kind="one_time"),
            FeeItem(
                name="County Health Permit",
                amount_cents=70000,
                kind="recurring",
                cadence="annual",
            ),
        ),
    ),
    "joshua_tree": FeeSchedule(
        jurisdiction="joshua_tree",
        paperwork=("San Bernardino Application", "Water System Disclosure"),
        fees=(
            FeeItem(name="Environmental Health Review", amount_cents=25000, kind="one_time"),
            FeeItem(
                name="San Bernardino County Permit",
                amount_cents=64000,
                kind="recurring",
                cadence="annual",
            ),
        ),
    ),
}


def _load_schedule(city_norm: str, *, original: str) -> FeeSchedule:
    try:
        return _FEE_SCHEDULES[city_norm]
    except KeyError as exc:  # pragma: no cover - FastAPI handles conversion
        raise HTTPException(status_code=404, detail=f"Unsupported city '{original}'") from exc


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
    schedule = _load_schedule(city_norm, original=city)

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
    schedule = _load_schedule(city_norm, original=city)

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


__all__ = ["router"]

"""City fee schedules exposed via the public API gateway."""
from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, HTTPException

from api.routes._city_utils import normalize_city

router = APIRouter()

_FEE_SCHEDULES: dict[str, dict[str, object]] = {
    "san_francisco": {
        "jurisdiction": "san_francisco",
        "paperwork": ["Application Form A-FOOD", "Plan Review Checklist PRC-12"],
        "fees": [
            {"name": "Food Facility Plan Review", "amount_cents": 45000, "kind": "one_time"},
            {
                "name": "Annual Health Permit",
                "amount_cents": 98000,
                "kind": "recurring",
                "cadence": "annual",
            },
            {
                "name": "Reinspection Fee",
                "amount_cents": 30000,
                "kind": "incremental",
                "unit": "per_reinspection",
            },
        ],
    },
    "oakland": {
        "jurisdiction": "oakland",
        "paperwork": ["Environmental Health Application", "Menu Worksheet"],
        "fees": [
            {"name": "Plan Review", "amount_cents": 38000, "kind": "one_time"},
            {
                "name": "Annual Health Permit",
                "amount_cents": 82000,
                "kind": "recurring",
                "cadence": "annual",
            },
        ],
    },
    "berkeley": {
        "jurisdiction": "berkeley",
        "paperwork": ["Retail Food Application", "Floor Plan Set"],
        "fees": [
            {"name": "Plan Check", "amount_cents": 42000, "kind": "one_time"},
            {
                "name": "Retail Food License",
                "amount_cents": 90000,
                "kind": "recurring",
                "cadence": "annual",
            },
        ],
    },
    "san_jose": {
        "jurisdiction": "san_jose",
        "paperwork": ["Santa Clara Food Permit Application", "Equipment Schedule"],
        "fees": [
            {"name": "Plan Review", "amount_cents": 40000, "kind": "one_time"},
            {
                "name": "Operating Permit",
                "amount_cents": 76000,
                "kind": "recurring",
                "cadence": "annual",
            },
        ],
    },
    "palo_alto": {
        "jurisdiction": "palo_alto",
        "paperwork": ["Santa Clara Health Application", "Menu Submission"],
        "fees": [
            {"name": "Plan Review", "amount_cents": 36000, "kind": "one_time"},
            {
                "name": "County Health Permit",
                "amount_cents": 70000,
                "kind": "recurring",
                "cadence": "annual",
            },
        ],
    },
    "joshua_tree": {
        "jurisdiction": "joshua_tree",
        "paperwork": ["San Bernardino Application", "Water System Disclosure"],
        "fees": [
            {
                "name": "Environmental Health Review",
                "amount_cents": 25000,
                "kind": "one_time",
            },
            {
                "name": "San Bernardino County Permit",
                "amount_cents": 64000,
                "kind": "recurring",
                "cadence": "annual",
            },
        ],
    },
}


def _totals(fees: List[Dict[str, object]]) -> dict[str, int]:
    one_time = sum(int(f["amount_cents"]) for f in fees if f.get("kind") == "one_time")
    recurring = sum(int(f["amount_cents"]) for f in fees if f.get("kind") == "recurring")
    incremental_count = sum(1 for f in fees if f.get("kind") == "incremental")
    return {
        "one_time_cents": one_time,
        "recurring_annualized_cents": recurring,
        "incremental_fee_count": incremental_count,
    }


@router.get("/{city}/fees")
def get_city_fees(city: str) -> dict[str, object]:
    """Return the normalized fee schedule for the provided city."""

    try:
        city_norm = normalize_city(city)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unsupported city '{city}'") from exc

    schedule = _FEE_SCHEDULES.get(city_norm)
    if not schedule:
        raise HTTPException(status_code=404, detail=f"Unsupported city '{city}'")

    fees: List[Dict[str, object]] = list(schedule["fees"])  # type: ignore[assignment]
    return {
        "jurisdiction": schedule["jurisdiction"],
        "paperwork": schedule["paperwork"],
        "fees": fees,
        "totals": _totals(fees),
        "validation": {"is_valid": True, "issues": []},
    }
