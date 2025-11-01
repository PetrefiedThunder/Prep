"""Joshua Tree Department of Public Health fee schedule."""

from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeItem,
    FeeSchedule,
    make_fee_schedule as build_schedule,
)


def make_fee_schedule() -> FeeSchedule:
    paperwork = [
        "San Bernardino County Health Permit Application",
        "Environmental Health Plan Check",
    ]
    fees = [
        FeeItem(name="Initial Health Permit", amount_cents=31200, kind="one_time"),
        FeeItem(
            name="Annual Health Permit Renewal",
            amount_cents=21800,
            kind="recurring",
            cadence="annual",
        ),
        FeeItem(
            name="Reinspection Fee",
            amount_cents=9400,
            kind="incremental",
            unit="per_reinspection",
            incremental=True,
        ),
    ]
    return build_schedule("joshua_tree", paperwork=paperwork, fees=fees)
