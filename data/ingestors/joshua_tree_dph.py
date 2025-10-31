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
