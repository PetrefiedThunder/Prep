"""Smoke tests for the v2 food safety compliance engine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from prep.compliance.food_safety_compliance_engine import FoodSafetyComplianceEngine

UTC = UTC


def iso(days_offset: int) -> str:
    """Return an ISO-8601 timestamp offset by ``days_offset`` days."""

    value = datetime.now(UTC).replace(microsecond=0) + timedelta(days=days_offset)
    return value.isoformat().replace("+00:00", "Z")


def build_green_path_payload() -> dict[str, Any]:
    """Return a fully compliant kitchen payload."""

    return {
        "license_info": {
            "license_number": "VALID-001",
            "license_type": "restaurant",
            "issue_date": iso(-400),
            "expiration_date": iso(400),
            "county_fips": "06037",
            "status": "active",
        },
        "inspection_history": [
            {
                "inspection_date": iso(-30),
                "overall_score": 97,
                "violations": [],
                "establishment_closed": False,
            }
        ],
        "certifications": [
            {"type": "ServSafe Manager", "status": "active", "expiration_date": iso(365)},
            {"type": "Allergen Awareness", "status": "active", "expiration_date": iso(365)},
        ],
        "equipment": [
            {
                "type": "refrigeration",
                "commercial_grade": True,
                "nsf_certified": True,
                "photo_url": "https://example.com/fridge.jpg",
            },
            {
                "type": "handwashing_station",
                "commercial_grade": True,
                "nsf_certified": True,
                "photo_url": "https://example.com/sink.jpg",
            },
        ],
        "insurance": {
            "policy_number": "INS-123456",
            "provider": "Commercial Insurance Co",
            "expiration_date": iso(365),
        },
        "photos": [
            {"url": "https://example.com/kitchen1.jpg"},
            {"url": "https://example.com/kitchen2.jpg"},
            {"url": "https://example.com/kitchen3.jpg"},
        ],
        "pest_control_records": [
            {"service_date": iso(-45), "provider": "Pest Control Inc"},
        ],
        "cleaning_logs": [
            {"date": iso(-7), "tasks_completed": ["sanitize", "deep_clean"]},
        ],
    }


@pytest.fixture()
def engine() -> FoodSafetyComplianceEngine:
    return FoodSafetyComplianceEngine()


def test_green_path_is_booking_ready(engine: FoodSafetyComplianceEngine) -> None:
    payload = build_green_path_payload()

    report = engine.generate_report(payload)
    assert pytest.approx(report.overall_compliance_score, rel=1e-6) == 1.0
    assert not report.violations_found

    can_book, critical = engine.validate_for_booking(payload)
    assert can_book is True
    assert not critical

    badge = engine.generate_kitchen_safety_badge(payload)
    assert badge["badge_level"] in {"gold", "silver"}
    assert badge["score"] >= 95
    assert badge["highlights"] and "ServSafe" in " ".join(badge["highlights"])
    assert badge["can_accept_bookings"] is True


def test_expired_license_blocks_bookings(engine: FoodSafetyComplianceEngine) -> None:
    payload = build_green_path_payload()
    payload["license_info"]["expiration_date"] = iso(-1)

    report = engine.generate_report(payload)
    violations = {v.rule_id: v for v in report.violations_found}

    assert "fs_license_1" in violations
    assert violations["fs_license_1"].severity == "critical"

    can_book, critical = engine.validate_for_booking(payload)
    assert can_book is False
    assert any(v.rule_id == "fs_license_1" for v in critical)


def test_low_inspection_score_triggers_critical_violation(
    engine: FoodSafetyComplianceEngine,
) -> None:
    payload = build_green_path_payload()
    payload["inspection_history"][0]["overall_score"] = 60

    report = engine.generate_report(payload)
    assert any(
        v.rule_id == "fs_inspect_2" and v.severity == "critical" for v in report.violations_found
    )


def test_missing_handwashing_station_is_critical(engine: FoodSafetyComplianceEngine) -> None:
    payload = build_green_path_payload()
    payload["equipment"] = [payload["equipment"][0]]  # drop the handwashing station

    report = engine.generate_report(payload)
    assert any(v.rule_id == "fs_equip_3" for v in report.violations_found)


def test_missing_or_expired_insurance_is_blocking(engine: FoodSafetyComplianceEngine) -> None:
    payload = build_green_path_payload()
    payload["insurance"]["expiration_date"] = iso(-10)

    report = engine.generate_report(payload)
    assert any(
        v.rule_id == "fs_prep_1" and v.severity == "critical" for v in report.violations_found
    )


def test_invalid_dates_emit_data_validation_violation(engine: FoodSafetyComplianceEngine) -> None:
    payload: dict[str, Any] = {
        "license_info": {
            "license_number": "INVALID",
            "status": "active",
            "expiration_date": "not-a-date",
        }
    }

    violations = engine.validate(payload)
    assert len(violations) == 1
    violation = violations[0]
    assert violation.rule_id == "data_validation"
    assert violation.severity == "critical"
    assert "validation_errors" in violation.context


def test_engine_is_idempotent(engine: FoodSafetyComplianceEngine) -> None:
    payload = build_green_path_payload()

    first = engine.generate_report(payload)
    second = engine.generate_report(payload)

    assert first.overall_compliance_score == second.overall_compliance_score
    assert [v.rule_id for v in first.violations_found] == [
        v.rule_id for v in second.violations_found
    ]
