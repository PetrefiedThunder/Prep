from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeItem,
    make_fee_schedule as build_schedule,
)


def make_fee_schedule():
    fees = [
        FeeItem(name="Plan Check", amount_cents=42000, kind="one_time"),
        FeeItem(
            name="Retail Food License",
            amount_cents=90000,
            kind="recurring",
            cadence="annual",
        ),
    ]
    paperwork = ["Retail Food Application", "Floor Plan Set"]
    return build_schedule("berkeley", paperwork=paperwork, fees=fees)
