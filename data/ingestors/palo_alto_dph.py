from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeItem,
    make_fee_schedule as build_schedule,
)


def make_fee_schedule():
    fees = [
        FeeItem(name="Plan Review", amount_cents=36000, kind="one_time"),
        FeeItem(
            name="County Health Permit",
            amount_cents=70000,
            kind="recurring",
            cadence="annual",
        ),
    ]
    paperwork = ["Santa Clara Health Application", "Menu Submission"]
    return build_schedule("palo_alto", paperwork=paperwork, fees=fees)
