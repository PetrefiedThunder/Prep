from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List

from .base_engine import ComplianceEngine, ComplianceReport
from .dol_reg_compliance_engine import DOLRegComplianceEngine
from .gdpr_ccpa_core import GDPRCCPACore
from .hbs_model_validator import HBSModelValidator
from .lse_impact_simulator import LondonStockExchangeSimulator
from .multivoice_compliance_ui import MultiVoiceComplianceUI


class ComplianceCoordinator:
    """Orchestrates multiple compliance engines."""

    def __init__(self) -> None:
        self.engines: Dict[str, ComplianceEngine] = {}
        self.logger = logging.getLogger("compliance.coordinator")
        if not self.logger.handlers:
            self.logger.addHandler(logging.NullHandler())
        self._initialize_engines()

    def _initialize_engines(self) -> None:
        self.engines = {
            "dol": DOLRegComplianceEngine(),
            "privacy": GDPRCCPACore(),
            "hbs": HBSModelValidator(),
            "lse": LondonStockExchangeSimulator(),
            "ui": MultiVoiceComplianceUI(),
        }
        self.logger.info("Initialized %d compliance engines", len(self.engines))

    def run_comprehensive_audit(self, data: Dict[str, Any]) -> Dict[str, ComplianceReport]:
        results: Dict[str, ComplianceReport] = {}

        for name, engine in self.engines.items():
            try:
                report = engine.generate_report(data)
                results[name] = report
                self.logger.info("Completed %s compliance check: %s", name, report.summary)
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.error("Error running %s compliance check: %s", name, exc)

                engine_version = getattr(engine, "engine_version", "unknown")
                raw_rule_versions = getattr(engine, "rule_versions", None)
                if isinstance(raw_rule_versions, dict):
                    rule_versions = dict(raw_rule_versions)
                else:
                    rule_versions = {}

                results[name] = ComplianceReport(
                    engine_name=engine.name,
                    engine_version=engine_version,
                    timestamp=datetime.now(timezone.utc),
                    total_rules_checked=0,
                    violations_found=[],
                    passed_rules=[],
                    summary=f"Error during compliance check: {exc}",
                    recommendations=["Review system logs for detailed error information"],
                    overall_compliance_score=0.0,
                    rule_versions=rule_versions,
                )

        return results

    def get_overall_compliance_score(self, reports: Dict[str, ComplianceReport]) -> float:
        if not reports:
            return 0.0
        total_score = sum(report.overall_compliance_score for report in reports.values())
        return total_score / len(reports)

    def generate_executive_summary(self, reports: Dict[str, ComplianceReport]) -> str:
        if not reports:
            return "No compliance reports available"

        scores = {name: report.overall_compliance_score for name, report in reports.items()}
        average_score = self.get_overall_compliance_score(reports)
        worst_area = min(scores.items(), key=lambda item: item[1]) if scores else ("n/a", 0.0)
        best_area = max(scores.items(), key=lambda item: item[1]) if scores else ("n/a", 0.0)
        critical_violations = sum(
            len([v for v in report.violations_found if v.severity == "critical"])
            for report in reports.values()
        )

        lines = [
            "COMPLIANCE EXECUTIVE SUMMARY",
            "============================",
            f"Overall Compliance Score: {average_score:.1%}",
            "",
            "Performance by Area:",
        ]
        lines.extend([f"  {name}: {score:.1%}" for name, score in scores.items()])
        lines.extend(
            [
                "",
                f"Key Insights:",
                f"- Best performing area: {best_area[0]} ({best_area[1]:.1%})",
                f"- Area needing attention: {worst_area[0]} ({worst_area[1]:.1%})",
                "",
                f"Critical Violations Found: {critical_violations}",
            ]
        )
        return "\n".join(lines)

    def get_priority_recommendations(self, reports: Dict[str, ComplianceReport]) -> List[str]:
        recommendations: List[str] = []
        critical_items: List[str] = []

        for report in reports.values():
            for violation in report.violations_found:
                if violation.severity in {"critical", "high"}:
                    critical_items.append(
                        f"- {violation.rule_name}: {violation.message}"
                    )
            recommendations.extend(report.recommendations)

        if critical_items:
            recommendations = ["ADDRESS CRITICAL VIOLATIONS IMMEDIATELY", *critical_items, *recommendations]

        seen: set[str] = set()
        deduped: List[str] = []
        for item in recommendations:
            if item not in seen:
                deduped.append(item)
                seen.add(item)

        return deduped[:10]
