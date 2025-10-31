"""Palo Alto fee schedule for food safety compliance."""

from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import FeeItem, FeeSchedule


def make_fee_schedule() -> FeeSchedule:
    paperwork = [
        "Business Registration",
        "County Environmental Health Permit",
    ]
    fees = [
        FeeItem(name="Business Registration", amount_cents=3100, kind="recurring", cadence="annual"),
        FeeItem(name="Environmental Health Permit", amount_cents=28600, kind="recurring", cadence="annual"),
        FeeItem(name="Facility Inspection", amount_cents=12200),
    ]
    return FeeSchedule(jurisdiction="palo_alto", paperwork=paperwork, fees=fees)
