from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeItem,
    make_fee_schedule as build_schedule,
)


def make_fee_schedule():
    fees = [
        FeeItem(name="Plan Review", amount_cents=40000, kind="one_time"),
        FeeItem(
            name="Operating Permit",
            amount_cents=76000,
            kind="recurring",
            cadence="annual",
        ),
    ]
    paperwork = ["Santa Clara Food Permit Application", "Equipment Schedule"]
    return build_schedule("san_jose", paperwork=paperwork, fees=fees)
