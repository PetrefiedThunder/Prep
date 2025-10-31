"""Fee schedule for City of Berkeley Environmental Health Division."""

from __future__ import annotations

from datetime import date

from .models import FeeComponent, FeeSchedule, validate_fee_schedule


def make_fee_schedule() -> FeeSchedule:
    """Return the City of Berkeley retail food permit fee schedule."""

    return FeeSchedule(
        jurisdiction="Berkeley, CA",
        program="Environmental Health Retail Food Permit",
        agency="City of Berkeley Environmental Health Division",
        renewal_frequency="annual",
        effective_date=date(2024, 7, 1),
        payment_methods=("online portal", "check", "credit card"),
        notes="Berkeley publishes a stand-alone fee schedule that mirrors Alameda County tiers but adds city surcharges.",
        references=(
            "https://berkeleyca.gov/sites/default/files/2024-06/environmental-health-fee-schedule.pdf",
        ),
        components=(
            FeeComponent(
                name="Base permit fee",
                amount=625.00,
                cadence="annual",
                description="Standard annual fee for a permanent retail food establishment.",
            ),
            FeeComponent(
                name="Plan review (new construction or major remodel)",
                amount=990.00,
                cadence="one-time",
                description="Includes initial inspection and administrative processing.",
            ),
            FeeComponent(
                name="Reinspection fee",
                amount=231.00,
                cadence="per reinspection",
                description="Levied when corrective actions require a follow-up inspection.",
            ),
        ),
    )


def validate_fee_schedule_berkeley(schedule: FeeSchedule | None = None) -> FeeSchedule:
    """Validate the Berkeley fee schedule."""

    return validate_fee_schedule(schedule or make_fee_schedule())


__all__ = ["make_fee_schedule", "validate_fee_schedule_berkeley"]
