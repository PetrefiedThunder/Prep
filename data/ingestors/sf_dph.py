"""Fee schedule for the San Francisco Department of Public Health."""

from __future__ import annotations

from datetime import date

from .models import FeeComponent, FeeSchedule, validate_fee_schedule


def make_fee_schedule() -> FeeSchedule:
    """Return the FY2024 San Francisco retail food fee schedule."""

    return FeeSchedule(
        jurisdiction="San Francisco, CA",
        program="Retail Food Facility Permit",
        agency="San Francisco Department of Public Health",
        renewal_frequency="annual",
        effective_date=date(2024, 7, 1),
        payment_methods=("online portal", "mail-in check"),
        notes=(
            "Fees mirror the Environmental Health Branch publication for the 2024-2025 "
            "fiscal year and include standard inspection charges."
        ),
        references=(
            "https://www.sfdph.org/dph/files/EHSdocs/ehsFood/2024-food-fees.pdf",
        ),
        components=(
            FeeComponent(
                name="Base permit fee (0-2000 sq ft)",
                amount=686.00,
                cadence="annual",
                description="Annual permit for retail food facilities under 2,000 square feet.",
            ),
            FeeComponent(
                name="Plan review (tenant improvement or new construction)",
                amount=876.00,
                cadence="one-time",
                description="Plan check required prior to opening or significant remodels.",
            ),
            FeeComponent(
                name="Reinspection fee",
                amount=226.00,
                cadence="per reinspection",
                description="Assessed when follow-up inspections are required to verify corrections.",
            ),
        ),
    )


def validate_fee_schedule_sf(schedule: FeeSchedule | None = None) -> FeeSchedule:
    """Validate the San Francisco fee schedule, optionally using *schedule*."""

    return validate_fee_schedule(schedule or make_fee_schedule())


__all__ = ["make_fee_schedule", "validate_fee_schedule_sf"]
