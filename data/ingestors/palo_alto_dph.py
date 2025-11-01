"""Palo Alto fee schedule for environmental health permits."""

from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeItem,
    FeeSchedule,
    make_fee_schedule as build_schedule,
)


def make_fee_schedule() -> FeeSchedule:
    paperwork = ["Environmental Health Application", "Fire Marshal Sign-off"]
    fees = [
        FeeItem(name="Plan Review", amount_cents=58500, kind="one_time"),
        FeeItem(
            name="Retail Food Permit",
            amount_cents=74200,
            kind="recurring",
            cadence="annual",
        ),
    ]
    return build_schedule("palo_alto", paperwork=paperwork, fees=fees)
