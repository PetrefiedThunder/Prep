"""Fee schedule for San Bernardino County Environmental Health (Joshua Tree)."""

from __future__ import annotations

from datetime import date

from .models import FeeComponent, FeeSchedule, validate_fee_schedule


def make_fee_schedule() -> FeeSchedule:
    """Return the San Bernardino County retail food fee schedule for Joshua Tree."""

    return FeeSchedule(
        jurisdiction="Joshua Tree, CA",
        program="San Bernardino County Retail Food Permit",
        agency="San Bernardino County Department of Public Health, Environmental Health Services",
        renewal_frequency="annual",
        effective_date=date(2024, 7, 1),
        payment_methods=("online portal", "mail-in check", "in-person counter"),
        notes=(
            "Joshua Tree kitchens are regulated by San Bernardino County; the schedule "
            "covers standard annual permits and common supplemental charges."
        ),
        references=(
            "https://wp.sbcounty.gov/dph/ehs/fees/2024-food-program-fees.pdf",
        ),
        components=(
            FeeComponent(
                name="Annual health permit",
                amount=493.00,
                cadence="annual",
                description="Required for permanent food facilities operating within the High Desert region.",
            ),
            FeeComponent(
                name="Plan review (new facility or remodel)",
                amount=712.00,
                cadence="one-time",
                description="Plan check performed prior to construction approval.",
            ),
            FeeComponent(
                name="Reinspection fee",
                amount=231.00,
                cadence="per reinspection",
                description="Assessed when a compliance inspection must be repeated due to violations.",
            ),
        ),
    )


def validate_fee_schedule_joshua_tree(schedule: FeeSchedule | None = None) -> FeeSchedule:
    """Validate the Joshua Tree/San Bernardino County fee schedule."""

    return validate_fee_schedule(schedule or make_fee_schedule())


__all__ = ["make_fee_schedule", "validate_fee_schedule_joshua_tree"]
"""Joshua Tree fee schedule for desert community operations."""

from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import FeeItem, FeeSchedule


def make_fee_schedule() -> FeeSchedule:
    paperwork = [
        "San Bernardino County Health Permit",
    ]
    fees = [
        FeeItem(name="County Health Permit", amount_cents=24800, kind="recurring", cadence="annual"),
        FeeItem(name="Well Water Testing", amount_cents=9500, kind="recurring", cadence="semiannual"),
        FeeItem(name="Site Inspection", amount_cents=7800),
    ]
    return FeeSchedule(jurisdiction="joshua_tree", paperwork=paperwork, fees=fees)
from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import (
    FeeItem,
    make_fee_schedule as build_schedule,
)


def make_fee_schedule():
    fees = [
        FeeItem(name="Environmental Health Review", amount_cents=25000, kind="one_time"),
        FeeItem(
            name="San Bernardino County Permit",
            amount_cents=64000,
            kind="recurring",
            cadence="annual",
        ),
    ]
    paperwork = ["San Bernardino Application", "Water System Disclosure"]
    return build_schedule("joshua_tree", paperwork=paperwork, fees=fees)
