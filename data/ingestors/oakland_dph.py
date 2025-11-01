"""City of Oakland Department of Public Health fee schedule."""

from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeItem,
    FeeSchedule,
    make_fee_schedule as build_schedule,
)


def make_fee_schedule() -> FeeSchedule:
    paperwork = [
        "Plan Review Submission",
        "Business Tax Registration",
        "Health Permit Application",
    ]
    fees = [
        FeeItem(name="Plan Review", amount_cents=52000, kind="one_time"),
        FeeItem(
            name="Health Permit",
            amount_cents=68400,
            kind="recurring",
            cadence="annual",
        ),
        FeeItem(
            name="Reinspection",
            amount_cents=15800,
            kind="incremental",
            unit="per_reinspection",
            incremental=True,
        ),
    ]
    return build_schedule("oakland", paperwork=paperwork, fees=fees)
