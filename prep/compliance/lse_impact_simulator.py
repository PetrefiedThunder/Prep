from __future__ import annotations

from datetime import datetime, timezone
import random
from typing import Any, Dict, List

from .base_engine import (
    ComplianceEngine,
    ComplianceReport,
    ComplianceRule,
    ComplianceViolation,
)


class LondonStockExchangeSimulator(ComplianceEngine):
    """LSE impact simulation and compliance engine."""

    def __init__(self) -> None:
        super().__init__("LSE_Impact_Simulator")
        self.load_rules()
        self.market_conditions = {
            "volatility": 0.02,
            "trading_volume": 1_000_000,
            "market_sentiment": 0.5,
        }

    def load_rules(self) -> None:  # type: ignore[override]
        now = datetime.now(timezone.utc)
        self.rules = [
            ComplianceRule(
                id="lse_disclosure_1",
                name="Material Information Disclosure",
                description="Material information must be disclosed promptly and fairly",
                category="disclosure",
                severity="critical",
                applicable_regulations=["MAR", "FSMA"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="lse_market_abuse_1",
                name="Market Abuse Prevention",
                description="Prevent insider trading and market manipulation",
                category="market_abuse",
                severity="critical",
                applicable_regulations=["MAR"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="lse_reporting_1",
                name="Periodic Reporting",
                description="Companies must submit periodic financial reports",
                category="reporting",
                severity="high",
                applicable_regulations=["MAR", "Companies_Act"],
                created_at=now,
                updated_at=now,
            ),
            ComplianceRule(
                id="lse_corporate_governance_1",
                name="Corporate Governance",
                description="Adhere to corporate governance principles",
                category="governance",
                severity="medium",
                applicable_regulations=["UK_Code"],
                created_at=now,
                updated_at=now,
            ),
        ]

    def validate(self, data: Dict[str, Any]) -> List[ComplianceViolation]:  # type: ignore[override]
        violations: List[ComplianceViolation] = []

        violations.extend(self._validate_disclosure(data))
        violations.extend(self._validate_market_abuse(data))
        violations.extend(self._validate_reporting(data))
        violations.extend(self._validate_corporate_governance(data))

        return violations

    def simulate_impact(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        event_type = scenario.get("event_type", "generic")
        impact_magnitude = float(scenario.get("impact_magnitude", 0.1))

        base_price_impact = impact_magnitude * (1 + random.uniform(-0.2, 0.2))
        base_volume_impact = abs(impact_magnitude) * 2

        adjusted_price_impact = base_price_impact * (1 + self.market_conditions["volatility"])
        adjusted_volume_impact = base_volume_impact * (
            1 + self.market_conditions["market_sentiment"]
        )

        return {
            "event_type": event_type,
            "price_impact": adjusted_price_impact,
            "volume_impact": adjusted_volume_impact,
            "confidence": 0.85,
            "simulation_timestamp": datetime.now(timezone.utc),
            "market_conditions": self.market_conditions.copy(),
        }

    def _validate_disclosure(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []

        for event in data.get("material_events", []):
            disclosed = bool(event.get("disclosed", False))
            disclosure_time = event.get("disclosure_time")
            event_time = event.get("event_time")

            if not disclosed:
                violations.append(
                    ComplianceViolation(
                        rule_id="lse_disclosure_1",
                        rule_name="Material Information Disclosure",
                        message=(
                            f"Material event not disclosed: {event.get('description', 'Unnamed event')}"
                        ),
                        severity="critical",
                        context={
                            "event_id": event.get("id"),
                            "disclosed": disclosed,
                        },
                        timestamp=datetime.now(timezone.utc),
                    )
                )
            elif isinstance(disclosure_time, datetime) and isinstance(event_time, datetime):
                delay = (disclosure_time - event_time).total_seconds()
                if delay > 3600:
                    violations.append(
                        ComplianceViolation(
                            rule_id="lse_disclosure_1",
                            rule_name="Material Information Disclosure",
                            message=(
                                f"Material event disclosure delayed by {delay / 3600:.1f} hours"
                            ),
                            severity="high",
                            context={
                                "event_id": event.get("id"),
                                "delay_seconds": delay,
                            },
                            timestamp=datetime.now(timezone.utc),
                        )
                    )

        return violations

    def _validate_market_abuse(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []

        for trade in data.get("trades", []):
            if trade.get("suspicious", False):
                violations.append(
                    ComplianceViolation(
                        rule_id="lse_market_abuse_1",
                        rule_name="Market Abuse Prevention",
                        message="Suspicious trading activity detected",
                        severity="critical",
                        context={
                            "trade_id": trade.get("id"),
                            "suspicious_indicators": trade.get("indicators", []),
                        },
                        timestamp=datetime.now(timezone.utc),
                    )
                )

            if trade.get("insider", False):
                violations.append(
                    ComplianceViolation(
                        rule_id="lse_market_abuse_1",
                        rule_name="Market Abuse Prevention",
                        message="Potential insider trading detected",
                        severity="critical",
                        context={
                            "trade_id": trade.get("id"),
                            "insider_relationship": trade.get("relationship"),
                        },
                        timestamp=datetime.now(timezone.utc),
                    )
                )

        return violations

    def _validate_reporting(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []
        reports = data.get("financial_reports", [])
        required_reports = ["annual", "interim", "ad hoc"]

        for report_type in required_reports:
            if not any(report.get("type") == report_type for report in reports):
                violations.append(
                    ComplianceViolation(
                        rule_id="lse_reporting_1",
                        rule_name="Periodic Reporting",
                        message=f"Required {report_type} report not submitted",
                        severity="high",
                        context={
                            "missing_report_type": report_type,
                            "submitted_reports": [report.get("type") for report in reports],
                        },
                        timestamp=datetime.now(timezone.utc),
                    )
                )

        return violations

    def _validate_corporate_governance(self, data: Dict[str, Any]) -> List[ComplianceViolation]:
        violations: List[ComplianceViolation] = []
        governance = data.get("corporate_governance", {})
        required_elements = ["board_independence", "audit_committee", "remuneration_policy"]

        for element in required_elements:
            if not governance.get(element, False):
                violations.append(
                    ComplianceViolation(
                        rule_id="lse_corporate_governance_1",
                        rule_name="Corporate Governance",
                        message=f"Corporate governance element missing: {element}",
                        severity="medium",
                        context={
                            "missing_element": element,
                            "implemented_elements": [
                                key for key, value in governance.items() if value
                            ],
                        },
                        timestamp=datetime.now(timezone.utc),
                    )
                )

        return violations

    def generate_report(self, data: Dict[str, Any]) -> ComplianceReport:  # type: ignore[override]
        base_report = super().generate_report(data)
        simulation_results = self.simulate_impact(
            {"event_type": "compliance_review", "impact_magnitude": 0.05}
        )

        enhanced_recommendations = base_report.recommendations.copy()
        enhanced_recommendations.append(
            "Market impact simulation shows price sensitivity of "
            f"{simulation_results['price_impact']:.2%}"
        )

        return ComplianceReport(
            engine_name=base_report.engine_name,
            timestamp=base_report.timestamp,
            total_rules_checked=base_report.total_rules_checked,
            violations_found=base_report.violations_found,
            passed_rules=base_report.passed_rules,
            summary=base_report.summary + " (Market impact analysis completed)",
            recommendations=enhanced_recommendations,
            overall_compliance_score=base_report.overall_compliance_score,
        )
