from __future__ import annotations

from datetime import datetime, timezone

import pytest

from prep.compliance.base_engine import (
    ComplianceEngine,
    ComplianceReport,
    ComplianceRule,
    ComplianceViolation,
)


class DummyComplianceEngine(ComplianceEngine):
    def __init__(self) -> None:
        super().__init__("TestComplianceEngine", engine_version="9.9.9")
        self.load_rules()

    def load_rules(self) -> None:  # type: ignore[override]
        now = datetime.now()
        self.rules = [
            ComplianceRule(
                id="test_rule_1",
                name="Test Rule",
                description="A test rule",
                category="test",
                severity="medium",
                applicable_regulations=["TEST"],
                created_at=now,
                updated_at=now,
            )
        ]

    def validate(self, data):  # type: ignore[override]
        if data.get("valid", True):
            return []
        return [
            ComplianceViolation(
                rule_id="test_rule_1",
                rule_name="Test Rule",
                message="Test violation",
                severity="medium",
                context={"test": "data"},
                timestamp=datetime.now(timezone.utc),
                rule_version="1.0.0",
            )
        ]


def test_compliance_engine_initialization() -> None:
    engine = DummyComplianceEngine()
    assert engine.name == "TestComplianceEngine"
    assert len(engine.rules) == 1


def test_generate_report_with_valid_data() -> None:
    engine = DummyComplianceEngine()
    report = engine.generate_report({"valid": True})

    assert isinstance(report, ComplianceReport)
    assert report.engine_name == "TestComplianceEngine"
    assert report.total_rules_checked == 1
    assert report.synthetic_violation_count == 0
    assert report.synthetic_failures == []
    assert report.overall_compliance_score == 1.0
    assert not report.violations_found
    assert report.passed_rules == ["test_rule_1"]
    assert report.engine_version == "9.9.9"
    assert report.rule_versions == {}


def test_generate_report_with_violation() -> None:
    engine = DummyComplianceEngine()
    report = engine.generate_report({"valid": False})

    assert len(report.violations_found) == 1
    assert report.overall_compliance_score == 0.0
    assert report.synthetic_violation_count == 0
    assert report.synthetic_failures == []
    assert report.passed_rules == []


def test_generate_report_with_unknown_violation_affects_score() -> None:
    class UnknownViolationEngine(DummyComplianceEngine):
        def validate(self, data):  # type: ignore[override]
            return [
                ComplianceViolation(
                    rule_id="synthetic_error",
                    rule_name="Synthetic",
                    message="Synthetic violation",
                    severity="critical",
                    context={},
                    timestamp=datetime.now(timezone.utc),
                )
            ]

    engine = UnknownViolationEngine()
    report = engine.generate_report({"valid": True})

    assert report.total_rules_checked == 2
    assert report.synthetic_violation_count == 1
    assert report.synthetic_failures == ["synthetic_error"]
    assert pytest.approx(report.overall_compliance_score, rel=1e-6) == 0.5
    assert report.passed_rules == ["test_rule_1"]
