"""Berkeley fee schedule for retail food permits."""

from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import FeeItem, FeeSchedule


def make_fee_schedule() -> FeeSchedule:
    paperwork = [
        "Retail Food Application",
        "Grease Interceptor Documentation",
    ]
    fees = [
        FeeItem(name="Retail Food Permit", amount_cents=39800, kind="recurring", cadence="annual"),
        FeeItem(name="Wastewater Pretreatment", amount_cents=8200),
        FeeItem(name="After-hours Inspection", amount_cents=6300, kind="recurring", cadence="monthly", incremental=True),
    ]
    return FeeSchedule(jurisdiction="berkeley", paperwork=paperwork, fees=fees)
