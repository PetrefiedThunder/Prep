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
