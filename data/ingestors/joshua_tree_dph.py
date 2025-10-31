"""Joshua Tree fee schedule for desert community operations."""

from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import FeeItem, FeeSchedule


def make_fee_schedule() -> FeeSchedule:
    paperwork = [
        "San Bernardino County Health Permit",
    ]
    fees = [
        FeeItem(name="County Health Permit", amount_cents=24800, kind="recurring", cadence="annual"),
        FeeItem(name="Well Water Testing", amount_cents=9500, kind="recurring", cadence="semiannual"),
        FeeItem(name="Site Inspection", amount_cents=7800),
    ]
    return FeeSchedule(jurisdiction="joshua_tree", paperwork=paperwork, fees=fees)
from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeItem,
    make_fee_schedule as build_schedule,
)


def make_fee_schedule():
    fees = [
        FeeItem(name="Environmental Health Review", amount_cents=25000, kind="one_time"),
        FeeItem(
            name="San Bernardino County Permit",
            amount_cents=64000,
            kind="recurring",
            cadence="annual",
        ),
    ]
    paperwork = ["San Bernardino Application", "Water System Disclosure"]
    return build_schedule("joshua_tree", paperwork=paperwork, fees=fees)
