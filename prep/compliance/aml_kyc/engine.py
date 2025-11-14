"""AML and KYC compliance engine implementation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ...core.orchestration import ComplianceDomain, ComplianceEngine, RegulatoryUpdate


@dataclass
class RiskAssessment:
    risk_level: str
    score: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SanctionCheckResult:
    matches: list[dict[str, Any]] = field(default_factory=list)
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class TransactionMonitoringResult:
    suspicious_patterns: list[str] = field(default_factory=list)
    reviewed_transactions: int = 0


@dataclass
class AMLComplianceResult:
    risk_level: str
    sanction_matches: list[dict[str, Any]]
    suspicious_activities: list[str]
    required_reports: list[str]
    score: float
    schema_version: str = "aml-compliance.v1"
    domain: str = ComplianceDomain.AML_KYC.value


class AMLKYCEngine(ComplianceEngine):
    """Anti-money laundering compliance engine."""

    async def validate_compliance(
        self, entity_data: dict[str, Any], jurisdiction: str | None
    ) -> AMLComplianceResult:
        risk_assessment = await self.assess_risk(entity_data)
        sanction_checks = await self.check_sanctions_lists(entity_data)
        transaction_monitoring = await self.analyze_transaction_patterns(entity_data)

        required_reports = self.determine_filing_requirements(risk_assessment)

        return AMLComplianceResult(
            risk_level=risk_assessment.risk_level,
            sanction_matches=sanction_checks.matches,
            suspicious_activities=transaction_monitoring.suspicious_patterns,
            required_reports=required_reports,
            score=risk_assessment.score,
        )

    async def generate_evidence(self, requirements: Iterable[str]) -> dict[str, Any]:
        evidence: dict[str, Any] = {}
        now = datetime.now(UTC).isoformat()
        for requirement in requirements:
            if requirement == "customer_due_diligence":
                evidence[requirement] = {"report": "CDD summary", "generated_at": now}
            elif requirement == "transaction_monitoring":
                evidence[requirement] = {"report": "Monitoring logs", "generated_at": now}
        return evidence

    async def monitor_changes(self) -> list[RegulatoryUpdate]:
        update = RegulatoryUpdate(
            domain=ComplianceDomain.AML_KYC,
            description="FATF advisory update",
            effective_date=datetime.now(UTC),
            jurisdiction="global",
            references=["https://www.fatf-gafi.org"],
        )
        return [update]

    async def assess_risk(self, entity_data: dict[str, Any]) -> RiskAssessment:
        jurisdictions = entity_data.get("jurisdictions", [])
        num_high_risk = sum(1 for item in jurisdictions if item.get("risk") == "high")
        score = min(1.0, 0.2 + num_high_risk * 0.2)
        level = "high" if score > 0.6 else "medium" if score > 0.3 else "low"
        return RiskAssessment(
            risk_level=level, score=score, details={"jurisdictions": jurisdictions}
        )

    async def check_sanctions_lists(self, entity_data: dict[str, Any]) -> SanctionCheckResult:
        parties = entity_data.get("counterparties", [])
        matches = [party for party in parties if party.get("sanctioned", False)]
        return SanctionCheckResult(matches=matches)

    async def analyze_transaction_patterns(
        self, entity_data: dict[str, Any]
    ) -> TransactionMonitoringResult:
        transactions = entity_data.get("transactions", [])
        suspicious = [
            f"Transaction {tx.get('id')} exceeds threshold"
            for tx in transactions
            if tx.get("amount", 0) > entity_data.get("threshold", 10000)
        ]
        return TransactionMonitoringResult(
            suspicious_patterns=suspicious, reviewed_transactions=len(transactions)
        )

    def determine_filing_requirements(self, risk_assessment: RiskAssessment) -> list[str]:
        if risk_assessment.risk_level == "high":
            return ["File SAR", "Enhanced Due Diligence"]
        if risk_assessment.risk_level == "medium":
            return ["Enhanced Monitoring"]
        return ["Standard Monitoring"]


__all__ = ["AMLKYCEngine", "AMLComplianceResult", "RiskAssessment"]
