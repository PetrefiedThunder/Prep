"""San Jose Department of Public Health fee schedule."""

from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeItem,
    FeeSchedule,
    make_fee_schedule as build_schedule,
)


def make_fee_schedule() -> FeeSchedule:
    paperwork = ["Health Permit Application", "Hazardous Materials Disclosure"]
    fees = [
        FeeItem(name="Initial Health Permit", amount_cents=48800, kind="one_time"),
        FeeItem(
            name="Annual Permit Renewal",
            amount_cents=45200,
            kind="recurring",
            cadence="annual",
        ),
    ]
    return build_schedule("san_jose", paperwork=paperwork, fees=fees)
