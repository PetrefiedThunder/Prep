"""San Francisco Department of Public Health fee schedule."""

from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import FeeItem, FeeSchedule


def make_fee_schedule() -> FeeSchedule:
    paperwork = [
        "Health Permit Application",
        "Plan Review Packet",
        "Food Safety Manager Certificate",
    ]
    fees = [
        FeeItem(name="Health Permit", amount_cents=55400, kind="recurring", cadence="annual"),
        FeeItem(name="Plan Review", amount_cents=21400),
        FeeItem(
            name="Reinspection",
            amount_cents=9400,
            kind="recurring",
            cadence="monthly",
            incremental=True,
        ),
    ]
    return FeeSchedule(jurisdiction="san_francisco", paperwork=paperwork, fees=fees)
