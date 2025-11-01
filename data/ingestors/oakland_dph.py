"""City of Oakland Department of Public Health fee schedule."""
"""Fee schedule for Alameda County Department of Environmental Health (Oakland)."""

from __future__ import annotations

from datetime import date

from .models import FeeComponent, FeeSchedule, validate_fee_schedule


def make_fee_schedule() -> FeeSchedule:
    """Return the Alameda County (Oakland) retail food facility fee schedule."""

    return FeeSchedule(
        jurisdiction="Oakland, CA",
        program="Retail Food Facility Permit",
        agency="Alameda County Department of Environmental Health",
        renewal_frequency="annual",
        effective_date=date(2024, 7, 1),
        payment_methods=("online portal", "in-person counter"),
        notes=(
            "Oakland facilities are permitted through Alameda County Environmental Health; "
            "tiers reflect the 2024 fee resolution for permanent food facilities."
        ),
        references=(
            "https://deh.acgov.org/food/documents/2024-retail-food-fee-schedule.pdf",
        ),
        components=(
            FeeComponent(
                name="Base permit fee (0-2000 sq ft)",
                amount=585.00,
                cadence="annual",
                description="Annual operating permit for full-service food facilities.",
            ),
            FeeComponent(
                name="Initial plan review",
                amount=857.00,
                cadence="one-time",
                description="Required for new construction or major remodel projects.",
            ),
            FeeComponent(
                name="Reinspection fee",
                amount=341.00,
                cadence="per reinspection",
                description="Charged when compliance verification visits are needed after violations.",
            ),
        ),
    )


def validate_fee_schedule_oakland(schedule: FeeSchedule | None = None) -> FeeSchedule:
    """Validate the Alameda County/Oakland fee schedule."""

    return validate_fee_schedule(schedule or make_fee_schedule())


__all__ = ["make_fee_schedule", "validate_fee_schedule_oakland"]
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
from __future__ import annotations

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
