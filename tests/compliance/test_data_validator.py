"""Unit tests for the DataValidator utilities used by the food safety engine."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from prep.compliance.data_validator import DataValidator


@pytest.mark.parametrize(
    "value",
    [
        "2024-10-19T10:00:00Z",
        "2024-10-19",
        datetime.now(UTC).replace(microsecond=0).isoformat(),
    ],
)
def test_validate_date_string_accepts_valid_formats(value: str) -> None:
    """The validator accepts ISO-8601 timestamps with or without timezone markers."""

    assert DataValidator.validate_date_string(value) is True


@pytest.mark.parametrize(
    "value",
    ["not-a-date", "2024/10/19", "2024-13-01", "2024-10-19T30:00:00Z"],
)
def test_validate_date_string_rejects_invalid_formats(value: str) -> None:
    """The validator rejects malformed date strings."""

    assert DataValidator.validate_date_string(value) is False


def test_validate_kitchen_data_returns_no_errors_for_valid_payload() -> None:
    """A complete payload should produce no validation errors."""

    payload = {
        "license_info": {"license_number": "ABC-123", "status": "active"},
        "inspection_history": [
            {
                "inspection_date": "2024-01-01T00:00:00Z",
                "overall_score": 95,
                "violations": [],
                "establishment_closed": False,
            },
            {
                "inspection_date": "2024-02-01",
                "overall_score": 98,
                "violations": [],
                "establishment_closed": False,
            },
        ],
        "equipment": [
            {"type": "refrigerator", "commercial_grade": True, "nsf_certified": True},
            {
                "type": "handwashing_station",
                "commercial_grade": True,
                "nsf_certified": True,
            },
        ],
    }

    assert DataValidator.validate_kitchen_data(payload) == []


def test_validate_kitchen_data_returns_errors_for_invalid_payload() -> None:
    """Missing fields and malformed values are captured as validation errors."""

    payload = {
        "license_info": {"license_number": "", "status": ""},
        "inspection_history": [
            {},
            {"inspection_date": "invalid"},
        ],
        "equipment": [{"type": ""}],
    }

    errors = DataValidator.validate_kitchen_data(payload)

    assert "license_info.license_number is required" in errors
    assert "license_info.status is required" in errors
    assert any(entry.startswith("inspection_history[1]") for entry in errors)
    assert any(entry.endswith("must be an ISO-8601 date") for entry in errors)
    assert any(entry.startswith("equipment[1]") for entry in errors)


def test_sanitize_kitchen_data_strips_disallowed_fields_and_characters() -> None:
    """Sanitisation removes unexpected keys and strips dangerous characters."""

    payload = {
        "license_info": {"license_number": "<ABC>'\""},
        "unknown": "should be removed",
        "equipment": [
            {"type": "<script>oven</script>"},
            {"type": "sink", "notes": "<b>clean</b>"},
        ],
    }

    sanitized = DataValidator.sanitize_kitchen_data(payload)

    assert "unknown" not in sanitized
    assert sanitized["license_info"]["license_number"] == "ABC"
    equipment_types = [item["type"] for item in sanitized["equipment"]]
    assert equipment_types == ["scriptoven/script", "sink"]
    # Nested values should also be sanitised
    assert sanitized["equipment"][1]["notes"] == "bclean/b"
