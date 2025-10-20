from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from prep.compliance.food_safety_compliance_engine import FoodSafetyComplianceEngine


def iso(days_offset: int) -> str:
    """Return an ISO-8601 string offset from now by the given days."""

    value = datetime.now(UTC).replace(microsecond=0) + timedelta(days=days_offset)
    return value.isoformat().replace("+00:00", "Z")


@pytest.fixture()
def engine() -> FoodSafetyComplianceEngine:
    return FoodSafetyComplianceEngine()


def build_fully_compliant_kitchen() -> dict:
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
                "overall_score": 95,
                "violations": [],
                "establishment_closed": False,
            }
        ],
        "certifications": [
            {
                "type": "ServSafe",
                "status": "active",
                "expiration_date": iso(365),
            },
            {
                "type": "Allergen Training",
                "status": "active",
                "expiration_date": iso(365),
            },
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
                "photo_url": "https://example.com/sink.jpg",
            },
        ],
        "insurance": {
            "policy_number": "INS-123456",
            "provider": "Commercial Insurance Co",
            "expiration_date": iso(400),
        },
        "photos": [
            {"url": "https://example.com/kitchen1.jpg"},
            {"url": "https://example.com/kitchen2.jpg"},
            {"url": "https://example.com/kitchen3.jpg"},
        ],
        "pest_control_records": [
            {
                "service_date": iso(-30),
                "provider": "Pest Control Inc",
            }
        ],
        "cleaning_logs": [
            {"date": iso(-7), "tasks_completed": ["sanitize", "deep_clean"]}
        ],
    }


def test_engine_initialization(engine: FoodSafetyComplianceEngine) -> None:
    assert engine.name == "Food_Safety_Compliance_Engine"
    assert len(engine.rules) >= 16


def test_valid_kitchen_compliance(engine: FoodSafetyComplianceEngine) -> None:
    valid_kitchen = build_fully_compliant_kitchen()
    report = engine.generate_report(valid_kitchen)

    assert report.overall_compliance_score > 0.9
    assert not any(v.severity == "critical" for v in report.violations_found)

    can_book, critical_violations = engine.validate_for_booking(valid_kitchen)
    assert can_book is True
    assert not critical_violations


def test_expired_license_violation(engine: FoodSafetyComplianceEngine) -> None:
    expired_kitchen = {
        "license_info": {
            "license_number": "TEST-002",
            "license_type": "restaurant",
            "issue_date": iso(-2000),
            "expiration_date": iso(-10),
            "county_fips": "06037",
            "status": "active",
        }
    }

    report = engine.generate_report(expired_kitchen)
    critical_violations = [v for v in report.violations_found if v.severity == "critical"]
    assert critical_violations
    assert any("license" in v.rule_id for v in critical_violations)

    can_book, critical_violations = engine.validate_for_booking(expired_kitchen)
    assert can_book is False
    assert critical_violations


def test_suspended_license_violation(engine: FoodSafetyComplianceEngine) -> None:
    suspended_kitchen = {
        "license_info": {
            "license_number": "TEST-003",
            "license_type": "restaurant",
            "issue_date": iso(-400),
            "expiration_date": iso(400),
            "county_fips": "06037",
            "status": "suspended",
        }
    }

    report = engine.generate_report(suspended_kitchen)
    critical_violations = [v for v in report.violations_found if v.severity == "critical"]
    assert critical_violations
    assert any("license" in v.rule_id for v in critical_violations)


def test_low_inspection_score_violation(engine: FoodSafetyComplianceEngine) -> None:
    low_score_kitchen = {
        "license_info": {
            "license_number": "TEST-004",
            "status": "active",
        },
        "inspection_history": [
            {
                "inspection_date": iso(-30),
                "overall_score": 65,
                "violations": [],
                "establishment_closed": False,
            }
        ],
    }

    report = engine.generate_report(low_score_kitchen)
    critical_violations = [v for v in report.violations_found if v.severity == "critical"]
    assert critical_violations
    assert any("inspect" in v.rule_id for v in critical_violations)


def test_missing_food_safety_manager(engine: FoodSafetyComplianceEngine) -> None:
    kitchen = {
        "license_info": {
            "license_number": "TEST-005",
            "status": "active",
        },
        "inspection_history": [
            {
                "inspection_date": iso(-30),
                "overall_score": 90,
                "violations": [],
                "establishment_closed": False,
            }
        ],
        "certifications": [
            {
                "type": "General Training",
                "status": "active",
            }
        ],
    }

    report = engine.generate_report(kitchen)
    high_violations = [v for v in report.violations_found if v.severity == "high"]
    assert any("cert" in v.rule_id for v in high_violations)


def test_missing_handwashing_station(engine: FoodSafetyComplianceEngine) -> None:
    kitchen = {
        "license_info": {
            "license_number": "TEST-006",
            "status": "active",
        },
        "inspection_history": [
            {
                "inspection_date": iso(-30),
                "overall_score": 90,
                "violations": [],
                "establishment_closed": False,
            }
        ],
        "certifications": [
            {
                "type": "ServSafe",
                "status": "active",
            }
        ],
        "equipment": [
            {
                "type": "refrigeration",
                "commercial_grade": True,
            }
        ],
    }

    report = engine.generate_report(kitchen)
    critical_violations = [v for v in report.violations_found if v.severity == "critical"]
    assert any("equip" in v.rule_id for v in critical_violations)


def test_safety_badge_generation(engine: FoodSafetyComplianceEngine) -> None:
    kitchen = build_fully_compliant_kitchen()
    badge = engine.generate_kitchen_safety_badge(kitchen)

    assert badge["badge_level"] in {"gold", "silver"}
    assert badge["score"] >= 85
    assert badge["highlights"]
    assert not badge["concerns"]


def test_invalid_date_handling(engine: FoodSafetyComplianceEngine) -> None:
    kitchen = {
        "license_info": {
            "license_number": "TEST-008",
            "status": "active",
            "expiration_date": "invalid-date",
        }
    }

    report = engine.generate_report(kitchen)
    assert any(v.severity == "critical" for v in report.violations_found)


def test_empty_kitchen_data(engine: FoodSafetyComplianceEngine) -> None:
    report = engine.generate_report({})
    assert report.violations_found


def test_booking_validation(engine: FoodSafetyComplianceEngine) -> None:
    valid_kitchen = build_fully_compliant_kitchen()
    can_book, critical_violations = engine.validate_for_booking(valid_kitchen)
    assert can_book is True
    assert not critical_violations

    invalid_kitchen = {
        "license_info": {
            "license_number": "TEST-010",
            "status": "expired",
            "expiration_date": iso(-10),
        }
    }

    can_book, critical_violations = engine.validate_for_booking(invalid_kitchen)
    assert can_book is False
    assert critical_violations
