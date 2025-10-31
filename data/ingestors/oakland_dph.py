"""Oakland fee schedule for food facility operations."""

from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import FeeItem, FeeSchedule


def make_fee_schedule() -> FeeSchedule:
    paperwork = [
        "Environmental Health Permit",
        "Zoning Clearance",
    ]
    fees = [
        FeeItem(name="Environmental Health Permit", amount_cents=47200, kind="recurring", cadence="annual"),
        FeeItem(name="Initial Inspection", amount_cents=18900),
        FeeItem(
            name="Follow-up Inspection",
            amount_cents=7600,
            kind="recurring",
            cadence="quarterly",
            incremental=True,
        ),
    ]
    return FeeSchedule(jurisdiction="oakland", paperwork=paperwork, fees=fees)
