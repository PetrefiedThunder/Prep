"""Palo Alto fee schedule for environmental health permits."""

"""Fee schedule for Palo Alto (Santa Clara County Environmental Health)."""

from __future__ import annotations

from datetime import date

from .models import FeeComponent, FeeSchedule, validate_fee_schedule


def make_fee_schedule() -> FeeSchedule:
    """Return the Santa Clara County fee schedule as applied to Palo Alto kitchens."""

    return FeeSchedule(
        jurisdiction="Palo Alto, CA",
        program="Santa Clara County Retail Food Permit",
        agency="Santa Clara County Department of Environmental Health",
        renewal_frequency="annual",
        effective_date=date(2024, 7, 1),
        payment_methods=("online portal", "credit card", "check"),
        notes=(
            "Palo Alto operators are permitted through Santa Clara County; the schedule "
            "captures the fees most commonly triggered for shared and commercial kitchens."
        ),
        references=(
            "https://countyofsantaclara.gov/sites/g/files/exjcpb1121/files/2024-06/deh-fee-schedule-2024.pdf",
        ),
        components=(
            FeeComponent(
                name="Annual health permit",
                amount=718.00,
                cadence="annual",
                description="Annual operating permit for low to moderate risk retail food facilities.",
            ),
            FeeComponent(
                name="Plan review (tenant improvement)",
                amount=1091.00,
                cadence="one-time",
                description="Comprehensive plan check for new or modified facilities.",
            ),
            FeeComponent(
                name="Reinspection fee",
                amount=236.00,
                cadence="per reinspection",
                description="Charged for each follow-up inspection after a cited violation.",
            ),
        ),
    )


def validate_fee_schedule_palo_alto(schedule: FeeSchedule | None = None) -> FeeSchedule:
    """Validate the Palo Alto fee schedule."""

    return validate_fee_schedule(schedule or make_fee_schedule())


__all__ = ["make_fee_schedule", "validate_fee_schedule_palo_alto"]
"""Palo Alto fee schedule for food safety compliance."""

from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import FeeItem, FeeSchedule


def make_fee_schedule() -> FeeSchedule:
    paperwork = [
        "Business Registration",
        "County Environmental Health Permit",
    ]
    fees = [
        FeeItem(
            name="Business Registration", amount_cents=3100, kind="recurring", cadence="annual"
        ),
        FeeItem(
            name="Environmental Health Permit",
            amount_cents=28600,
            kind="recurring",
            cadence="annual",
        ),
        FeeItem(name="Facility Inspection", amount_cents=12200),
    ]
    return FeeSchedule(jurisdiction="palo_alto", paperwork=paperwork, fees=fees)


from __future__ import annotations

from apps.city_regulatory_service.jurisdictions.common.fees import (
    make_fee_schedule as build_schedule,
)


def make_fee_schedule() -> FeeSchedule:
    paperwork = ["Environmental Health Application", "Fire Marshal Sign-off"]
    fees = [
        FeeItem(name="Plan Review", amount_cents=58500, kind="one_time"),
        FeeItem(
            name="Retail Food Permit",
            amount_cents=74200,
            kind="recurring",
            cadence="annual",
        ),
    ]
    return build_schedule("palo_alto", paperwork=paperwork, fees=fees)
