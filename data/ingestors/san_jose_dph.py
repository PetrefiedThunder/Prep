"""San Jose Department of Public Health fee schedule."""

"""Fee schedule for Santa Clara County Department of Environmental Health (San Jose)."""

from __future__ import annotations

from datetime import date

from .models import FeeComponent, FeeSchedule, validate_fee_schedule


def make_fee_schedule() -> FeeSchedule:
    """Return the Santa Clara County retail food fee schedule for San Jose."""

    return FeeSchedule(
        jurisdiction="San Jose, CA",
        program="Santa Clara County Retail Food Permit",
        agency="Santa Clara County Department of Environmental Health",
        renewal_frequency="annual",
        effective_date=date(2024, 7, 1),
        payment_methods=("online portal", "credit card", "check"),
        notes=(
            "Santa Clara County manages San Jose food permits; values capture the core "
            "permit, plan review, and technology surcharge fees for FY2024."
        ),
        references=(
            "https://countyofsantaclara.gov/sites/g/files/exjcpb1121/files/2024-06/deh-fee-schedule-2024.pdf",
        ),
        components=(
            FeeComponent(
                name="Annual health permit",
                amount=850.00,
                cadence="annual",
                description="Permanent food facility operating permit.",
            ),
            FeeComponent(
                name="Plan review (full service kitchen)",
                amount=945.00,
                cadence="one-time",
                description="Applies to new facilities or major remodels requiring plan check.",
            ),
            FeeComponent(
                name="Technology surcharge",
                amount=65.00,
                cadence="annual",
                description="County surcharge supporting electronic inspection systems.",
            ),
        ),
    )


def validate_fee_schedule_san_jose(schedule: FeeSchedule | None = None) -> FeeSchedule:
    """Validate the San Jose/Santa Clara County fee schedule."""

    return validate_fee_schedule(schedule or make_fee_schedule())


__all__ = ["make_fee_schedule", "validate_fee_schedule_san_jose"]
"""San Jose fee schedule for food facility permitting."""

from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import FeeItem, FeeSchedule


def make_fee_schedule() -> FeeSchedule:
    paperwork = [
        "Unified Permit Application",
        "Fire Safety Inspection Report",
    ]
    fees = [
        FeeItem(name="Operating Permit", amount_cents=43600, kind="recurring", cadence="annual"),
        FeeItem(name="Initial Plan Review", amount_cents=16600),
        FeeItem(name="Change of Ownership", amount_cents=12800),
    ]
    return FeeSchedule(jurisdiction="san_jose", paperwork=paperwork, fees=fees)


from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import (
    make_fee_schedule as build_schedule,
)


def make_fee_schedule() -> FeeSchedule:
    paperwork = ["Health Permit Application", "Hazardous Materials Disclosure"]
    fees = [
        FeeItem(name="Initial Health Permit", amount_cents=48800, kind="one_time"),
        FeeItem(
            name="Annual Permit Renewal",
            amount_cents=45200,
            kind="recurring",
            cadence="annual",
        ),
    ]
    return build_schedule("san_jose", paperwork=paperwork, fees=fees)
