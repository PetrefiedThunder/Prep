from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeItem,
    make_fee_schedule as build_schedule,
)


def make_fee_schedule():
    fees = [
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
        ),
    ]
    paperwork = ["Application Form A-FOOD", "Plan Review Checklist PRC-12"]
    return build_schedule("san_francisco", paperwork=paperwork, fees=fees)
