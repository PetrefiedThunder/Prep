"""Berkeley fee schedule for retail food permits."""

from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeItem,
    FeeSchedule,
    make_fee_schedule as build_schedule,
)


def make_fee_schedule() -> FeeSchedule:
    paperwork = ["Retail Food Application", "Floor Plan Set"]
    fees = [
        FeeItem(name="Plan Check", amount_cents=42000, kind="one_time"),
        FeeItem(
            name="Retail Food License",
            amount_cents=90000,
            kind="recurring",
            cadence="annual",
        ),
    ]
    return build_schedule("berkeley", paperwork=paperwork, fees=fees)
