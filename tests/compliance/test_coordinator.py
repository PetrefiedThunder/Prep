from __future__ import annotations

from datetime import datetime

import pytest

from prep.compliance.base_engine import ComplianceEngine, ComplianceReport
from prep.compliance.coordinator import ComplianceCoordinator


class _FailingEngine(ComplianceEngine):
    def __init__(self) -> None:
        super().__init__(name="failing", engine_version="9.9.9")
        self.rule_versions = {"rule-001": "2024.01"}

    def load_rules(self) -> None:  # pragma: no cover - not needed for tests
        self.rules = []

    def validate(self, data):  # type: ignore[override]
        raise RuntimeError("synthetic failure")


def test_coordinator_initialization() -> None:
    coordinator = ComplianceCoordinator()
    assert {"dol", "privacy", "hbs", "lse", "ui"}.issubset(coordinator.engines.keys())


def test_run_comprehensive_audit() -> None:
    coordinator = ComplianceCoordinator()
    data = {
        "employees": [{"id": "emp1", "hours_worked": 40, "hourly_rate": 20}],
        "users": [{"id": "user1", "consent_given": True, "consent_timestamp": "2023-01-01"}],
    }

    reports = coordinator.run_comprehensive_audit(data)
    assert len(reports) == 5
    assert all(isinstance(report, ComplianceReport) for report in reports.values())


def test_get_overall_compliance_score() -> None:
    coordinator = ComplianceCoordinator()
    reports = {
        "engine1": ComplianceReport(
            engine_name="engine1",
            timestamp=datetime.now(),
            total_rules_checked=5,
            violations_found=[],
            passed_rules=["rule1"],
            summary="All good",
            recommendations=[],
            overall_compliance_score=0.8,
            engine_version="1.0.0",
            rule_versions={"rule1": "v1"},
        ),
        "engine2": ComplianceReport(
            engine_name="engine2",
            timestamp=datetime.now(),
            total_rules_checked=5,
            violations_found=[],
            passed_rules=["rule1"],
            summary="All good",
            recommendations=[],
            overall_compliance_score=0.6,
            engine_version="1.0.0",
            rule_versions={"rule1": "v1"},
        ),
    }
    assert coordinator.get_overall_compliance_score(reports) == 0.7


def test_generate_executive_summary() -> None:
    coordinator = ComplianceCoordinator()
    reports = coordinator.run_comprehensive_audit({})
    summary = coordinator.generate_executive_summary(reports)
    assert "COMPLIANCE EXECUTIVE SUMMARY" in summary


def test_get_priority_recommendations() -> None:
    coordinator = ComplianceCoordinator()
    reports = coordinator.run_comprehensive_audit({})
    recommendations = coordinator.get_priority_recommendations(reports)
    assert recommendations


def test_run_comprehensive_audit_handles_engine_failure() -> None:
    coordinator = ComplianceCoordinator()
    failing_engine = _FailingEngine()
    coordinator.engines = {"failing": failing_engine}

    reports = coordinator.run_comprehensive_audit({})

    assert "failing" in reports
    report = reports["failing"]
    assert isinstance(report, ComplianceReport)
    assert report.engine_version == failing_engine.engine_version
    assert report.rule_versions == failing_engine.rule_versions
    assert "Error during compliance check" in report.summary


def test_coordinator_with_subset_of_engines() -> None:
    coordinator = ComplianceCoordinator(enabled_engines=["dol", "privacy"])
    assert set(coordinator.engines.keys()) == {"dol", "privacy"}


def test_coordinator_empty_enabled_engines() -> None:
    coordinator = ComplianceCoordinator(enabled_engines=[])
    assert coordinator.engines == {}


def test_coordinator_unknown_engine_key() -> None:
    with pytest.raises(ValueError, match="Unknown compliance engine keys requested"):
        ComplianceCoordinator(enabled_engines=["dol", "unknown"]) 
