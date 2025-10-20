from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional


@dataclass
class ComplianceRule:
    """Represents a compliance rule with metadata."""

    id: str
    name: str
    description: str
    category: str
    severity: str
    applicable_regulations: List[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class ComplianceViolation:
    """Represents a compliance violation found during validation."""

    rule_id: str
    rule_name: str
    message: str
    severity: str
    context: Dict[str, Any]
    timestamp: datetime
    rule_version: Optional[str] = None
    evidence_path: Optional[str] = None
    observed_value: Any = None


@dataclass
class ComplianceReport:
    """Comprehensive compliance report."""

    engine_name: str
    timestamp: datetime
    total_rules_checked: int
    violations_found: List[ComplianceViolation]
    passed_rules: List[str]
    summary: str
    recommendations: List[str]
    overall_compliance_score: float
    engine_version: str
    rule_versions: Dict[str, str]
    report_signature: Optional[str] = None


class ComplianceEngine(ABC):
    """Abstract base class for all compliance engines."""

    def __init__(self, name: Optional[str] = None, *, engine_version: str = "1.0.0") -> None:
        self.name = name or self.__class__.__name__
        self.engine_version = engine_version
        self.rules: List[ComplianceRule] = []
        self.rule_versions: Dict[str, str] = {}
        self.logger = logging.getLogger(f"compliance.{self.name}")
        if not self.logger.handlers:
            self.logger.addHandler(logging.NullHandler())

    @abstractmethod
    def load_rules(self) -> None:
        """Load compliance rules for this engine."""

    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        """Validate data against compliance rules."""

    def generate_report(self, data: Dict[str, Any]) -> ComplianceReport:
        """Generate a comprehensive compliance report for the provided data."""

        violations = self.validate(data)

        rule_ids = {rule.id for rule in self.rules}
        known_violation_ids = {
            violation.rule_id for violation in violations if violation.rule_id in rule_ids
        }
        passed_rules = [rule.id for rule in self.rules if rule.id not in known_violation_ids]
        unknown_violation_count = sum(
            1 for violation in violations if violation.rule_id not in rule_ids
        )

        total_evaluated = len(self.rules) + unknown_violation_count
        if total_evaluated == 0:
            score = 1.0
        else:
            score = len(passed_rules) / total_evaluated
            score = max(0.0, min(1.0, score))

        critical_violations = [v for v in violations if v.severity == "critical"]
        high_violations = [v for v in violations if v.severity == "high"]

        summary_parts: List[str] = []
        if critical_violations:
            summary_parts.append(f"{len(critical_violations)} critical violations")
        if high_violations:
            summary_parts.append(f"{len(high_violations)} high severity violations")
        if not violations:
            summary_parts.append("All compliance checks passed")

        summary = ", ".join(summary_parts) if summary_parts else "Compliance check completed"

        recommendations: List[str] = []
        if critical_violations:
            recommendations.append("Address critical violations immediately")
        if high_violations:
            recommendations.append("Review high severity violations promptly")
        if not violations:
            recommendations.append("Continue monitoring for compliance changes")

        return ComplianceReport(
            engine_name=self.name,
            timestamp=datetime.now(timezone.utc),
            total_rules_checked=total_evaluated,
            violations_found=violations,
            passed_rules=passed_rules,
            summary=summary,
            recommendations=recommendations,
            overall_compliance_score=score,
            engine_version=self.engine_version,
            rule_versions=dict(self.rule_versions),
        )

    def add_rule(self, rule: ComplianceRule) -> None:
        """Add a compliance rule to the engine."""

        self.rules.append(rule)
        self.logger.info("Added rule: %s", rule.name)
