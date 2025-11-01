"""San Francisco Department of Public Health fee schedule."""

from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeItem,
    FeeSchedule,
    make_fee_schedule as build_schedule,
)


def make_fee_schedule() -> FeeSchedule:
    paperwork = [
        "Health Permit Application",
        "Plan Review Packet",
        "Food Safety Manager Certificate",
    ]
    fees = [
        FeeItem(name="Health Permit", amount_cents=55400, kind="recurring", cadence="annual"),
        FeeItem(name="Plan Review", amount_cents=21400, kind="one_time"),
        FeeItem(
            name="Reinspection",
            amount_cents=9400,
            kind="incremental",
            unit="per_reinspection",
            incremental=True,
        ),
    ]
    return build_schedule("san_francisco", paperwork=paperwork, fees=fees)
