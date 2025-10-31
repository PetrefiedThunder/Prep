"""Oakland fee schedule for food facility operations."""

from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import FeeItem, FeeSchedule


def make_fee_schedule() -> FeeSchedule:
    paperwork = [
        "Environmental Health Permit",
        "Zoning Clearance",
    ]
    fees = [
        FeeItem(name="Environmental Health Permit", amount_cents=47200, kind="recurring", cadence="annual"),
        FeeItem(name="Initial Inspection", amount_cents=18900),
        FeeItem(
            name="Follow-up Inspection",
            amount_cents=7600,
            kind="recurring",
            cadence="quarterly",
            incremental=True,
        ),
    ]
    return FeeSchedule(jurisdiction="oakland", paperwork=paperwork, fees=fees)
from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeItem,
    make_fee_schedule as build_schedule,
)


def make_fee_schedule():
    fees = [
        FeeItem(name="Plan Review", amount_cents=38000, kind="one_time"),
        FeeItem(
            name="Annual Health Permit",
            amount_cents=82000,
            kind="recurring",
            cadence="annual",
        ),
    ]
    paperwork = ["Environmental Health Application", "Menu Worksheet"]
    return build_schedule("oakland", paperwork=paperwork, fees=fees)
