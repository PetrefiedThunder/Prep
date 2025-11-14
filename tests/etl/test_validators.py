"""Tests for ETL validation helpers."""

from __future__ import annotations

import pytest

from apps.city_regulatory_service.jurisdictions.common.fees import FeeItem, FeeSchedule
from etl.validators import (
    FeeValidationError,
    RequirementValidationError,
    validate_fee_schedule,
    validate_requirements,
)


def _build_schedule() -> FeeSchedule:
    return FeeSchedule(
        jurisdiction="testopolis",
        paperwork=("Form A",),
        fees=(
            FeeItem(name="Plan Review", amount_cents=5000, kind="one_time"),
            FeeItem(name="Annual Permit", amount_cents=12000, kind="recurring", cadence="annual"),
            FeeItem(
                name="Reinspection",
                amount_cents=2500,
                kind="incremental",
                unit="per_reinspection",
                incremental=True,
            ),
        ),
    )


def test_validate_fee_schedule_success() -> None:
    schedule = _build_schedule()
    summary = validate_fee_schedule(schedule, raise_on_error=False)

    assert summary.issues == []
    assert summary.counts_by_kind == {"one_time": 1, "recurring": 1, "incremental": 1}
    assert summary.totals["one_time_cents"] == 5000
    assert summary.totals["recurring_annualized_cents"] == 12000
    assert summary.totals["incremental_fee_count"] == 1


def test_validate_fee_schedule_detects_totals_mismatch() -> None:
    schedule = _build_schedule()
    with pytest.raises(FeeValidationError) as excinfo:
        validate_fee_schedule(
            {
                "fees": [item.dict() for item in schedule.fees],
                "totals": {
                    "one_time_cents": 1,
                    "recurring_annualized_cents": 0,
                    "incremental_fee_count": 0,
                },
            }
        )

    assert "one_time_cents" in str(excinfo.value)


def test_validate_requirements_success() -> None:
    requirements = [
        {"id": "req-1", "applies_to": ["kitchen_operator"], "severity": "blocking"},
        {"id": "req-2", "applies_to": ["food_business"], "severity": "conditional"},
        {"id": "req-3", "applies_to": ["marketplace_operator"], "severity": "advisory"},
        {"id": "req-4", "applies_to": ["platform_developer"], "severity": "advisory"},
    ]

    summary = validate_requirements(requirements, raise_on_error=False)

    assert summary.issues == []
    assert summary.blocking_count == 1
    assert summary.counts_by_party["food_business"] == 1


def test_validate_requirements_missing_severity() -> None:
    with pytest.raises(RequirementValidationError) as excinfo:
        validate_requirements([{"id": "req", "applies_to": ["food_business"], "severity": None}])

    assert "missing severity" in str(excinfo.value)
