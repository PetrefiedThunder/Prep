from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from prep.core.orchestration import ComplianceDomain
from prep.core.schema_validation import SchemaValidationError, SchemaValidator


@dataclass
class _Result:
    overall_compliance: float
    required_actions: list[str]
    checks: list[dict[str, Any]]
    summary: str = ""
    schema_version: str = "privacy-compliance.v1"


def test_schema_validator_accepts_valid_privacy_payload() -> None:
    validator = SchemaValidator()
    payload = _Result(
        overall_compliance=0.9,
        required_actions=["continue-monitoring"],
        checks=[
            {
                "name": "Consent",
                "passed": True,
                "severity": "medium",
                "details": "ok",
                "remediation": "",
            }
        ],
    )

    normalized = validator.ensure_valid(ComplianceDomain.GDPR_CCPA, payload)
    assert normalized["x-schema-version"] == "privacy-compliance.v1"
    assert normalized["domain"] == ComplianceDomain.GDPR_CCPA.value


def test_schema_validator_raises_for_missing_fields() -> None:
    validator = SchemaValidator()
    payload = {"overall_compliance": 1.0, "checks": []}

    with pytest.raises(SchemaValidationError) as exc:
        validator.ensure_valid(ComplianceDomain.GDPR_CCPA, payload)

    assert "required property" in " ".join(exc.value.errors)
