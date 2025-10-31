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
