from __future__ import annotations

from datetime import datetime

from prep.compliance.base_engine import (
    ComplianceEngine,
    ComplianceReport,
    ComplianceRule,
    ComplianceViolation,
)


class DummyComplianceEngine(ComplianceEngine):
    def __init__(self) -> None:
        super().__init__("TestComplianceEngine")
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
                timestamp=datetime.now(),
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
    assert report.overall_compliance_score == 1.0
    assert not report.violations_found
    assert report.passed_rules == ["test_rule_1"]


def test_generate_report_with_violation() -> None:
    engine = DummyComplianceEngine()
    report = engine.generate_report({"valid": False})

    assert len(report.violations_found) == 1
    assert report.overall_compliance_score == 0.0
    assert report.passed_rules == []
