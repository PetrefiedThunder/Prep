from __future__ import annotations

from datetime import datetime

from prep.compliance.base_engine import ComplianceReport
from prep.compliance.coordinator import ComplianceCoordinator


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
            synthetic_violation_count=0,
            synthetic_failures=[],
            violations_found=[],
            passed_rules=["rule1"],
            summary="All good",
            recommendations=[],
            overall_compliance_score=0.8,
            engine_version="1.0",
            rule_versions={},
        ),
        "engine2": ComplianceReport(
            engine_name="engine2",
            timestamp=datetime.now(),
            total_rules_checked=5,
            synthetic_violation_count=0,
            synthetic_failures=[],
            violations_found=[],
            passed_rules=["rule1"],
            summary="All good",
            recommendations=[],
            overall_compliance_score=0.6,
            engine_version="1.0",
            rule_versions={},
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
