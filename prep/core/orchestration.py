"""Enterprise compliance orchestration primitives."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Mapping, Optional

from .audit import AuditService
from .evidence_vault import EvidenceVault
from .schema_validation import SchemaValidationError, SchemaValidator

if TYPE_CHECKING:
    from .data_pipeline import UnifiedDataPipeline


class ComplianceDomain(Enum):
    """Supported compliance domains."""

    GDPR_CCPA = "privacy_regulations"
    AML_KYC = "anti_money_laundering"
    GAAP_IFRS = "accounting_standards"
    LEGAL_DISCOVERY = "ediscovery_compliance"
    FOOD_SAFETY = "commercial_kitchen"


@dataclass
class ComplianceResult:
    """Canonical result returned by compliance engines."""

    domain: ComplianceDomain
    is_compliant: bool
    score: float
    issues: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidencePackage:
    """Evidence generated for audits."""

    evidence_items: Dict[str, Any]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RegulatoryUpdate:
    """Represents a regulatory change surfaced by a compliance engine."""

    domain: ComplianceDomain
    description: str
    effective_date: datetime
    jurisdiction: Optional[str] = None
    references: List[str] = field(default_factory=list)


@dataclass
class UnifiedComplianceReport:
    """Aggregated compliance report across multiple domains."""

    entity_id: str
    assessment_date: datetime
    domain_results: Mapping[ComplianceDomain, Any]
    overall_risk_score: float
    notes: Optional[str] = None


class ComplianceEngine(ABC):
    """Abstract interface for asynchronous compliance engines."""

    @abstractmethod
    async def validate_compliance(
        self, entity_data: Dict[str, Any], jurisdiction: Optional[str]
    ) -> Any:
        """Validate entity data for a given jurisdiction."""

    @abstractmethod
    async def generate_evidence(self, requirements: Iterable[str]) -> Any:
        """Produce audit-ready evidence packages."""

    @abstractmethod
    async def monitor_changes(self) -> List[RegulatoryUpdate]:
        """Return recent regulatory updates monitored by this engine."""


class OrchestrationEngine:
    """Coordinates multi-domain compliance checks across engines."""

    def __init__(
        self,
        *,
        evidence_vault: EvidenceVault | None = None,
        schema_validator: SchemaValidator | None = None,
    ) -> None:
        from .data_pipeline import UnifiedDataPipeline

        self.engines: Dict[ComplianceDomain, ComplianceEngine] = {}
        self.data_pipeline: "UnifiedDataPipeline" = UnifiedDataPipeline()
        self.audit_trail = AuditService()
        self.evidence_vault = evidence_vault or EvidenceVault()
        self.schema_validator = schema_validator or SchemaValidator()

    def register_engine(self, domain: ComplianceDomain, engine: ComplianceEngine) -> None:
        """Register a compliance engine for a specific domain."""

        self.engines[domain] = engine

    async def orchestrate_compliance_check(
        self,
        domains: Iterable[ComplianceDomain],
        entity_data: Dict[str, Any],
        *,
        evidence_requirements: Mapping[ComplianceDomain, Iterable[str]] | None = None,
    ) -> UnifiedComplianceReport:
        """Execute a compliance assessment across multiple domains."""

        results: Dict[ComplianceDomain, Any] = {}
        jurisdiction = entity_data.get("jurisdiction")
        entity_id = str(entity_data.get("id", "unknown"))
        evidence_requirements = evidence_requirements or {}

        for domain in domains:
            engine = self.engines.get(domain)
            if engine is None:
                continue

            normalized_jurisdiction = (
                str(jurisdiction) if jurisdiction is not None else None
            )
            result = await engine.validate_compliance(entity_data, normalized_jurisdiction)
            try:
                normalized = self.schema_validator.ensure_valid(domain, result)
            except SchemaValidationError as exc:
                await self.audit_trail.record_validation_failure(
                    domain=domain,
                    entity_id=entity_id,
                    errors=exc.errors,
                )
                continue

            evidence_reference = None
            requirements = evidence_requirements.get(domain)
            if requirements:
                evidence_payload = await engine.generate_evidence(requirements)
                evidence_reference = self.evidence_vault.store(
                    entity_id=entity_id,
                    domain=domain,
                    evidence=evidence_payload,
                )

            results[domain] = result

            await self.audit_trail.record_compliance_check(
                domain=domain,
                entity_id=entity_id,
                result=result,
                schema_version=normalized.get("x-schema-version"),
                evidence_reference=evidence_reference,
            )

        return UnifiedComplianceReport(
            entity_id=str(entity_data.get("id", "unknown")),
            assessment_date=datetime.now(timezone.utc),
            domain_results=results,
            overall_risk_score=self.calculate_aggregate_risk(results.values()),
        )

    def calculate_aggregate_risk(self, results: Iterable[Any]) -> float:
        """Calculate an aggregate risk score from heterogeneous engine outputs."""

        risk_scores: List[float] = []
        for result in results:
            if result is None:
                continue

            if hasattr(result, "overall_compliance"):
                compliance_value = getattr(result, "overall_compliance")
                if isinstance(compliance_value, (int, float)):
                    risk_scores.append(max(0.0, min(1.0, 1 - float(compliance_value))))
            if hasattr(result, "risk_level"):
                level = str(getattr(result, "risk_level")).lower()
                mapping = {
                    "low": 0.25,
                    "moderate": 0.5,
                    "medium": 0.5,
                    "elevated": 0.75,
                    "high": 0.85,
                    "critical": 1.0,
                }
                risk_scores.append(mapping.get(level, 0.5))
            if hasattr(result, "score") and isinstance(getattr(result, "score"), (int, float)):
                risk_scores.append(max(0.0, min(1.0, 1 - float(getattr(result, "score")))))

        if not risk_scores:
            return 0.0

        return sum(risk_scores) / len(risk_scores)


__all__ = [
    "ComplianceDomain",
    "ComplianceResult",
    "EvidencePackage",
    "RegulatoryUpdate",
    "UnifiedComplianceReport",
    "ComplianceEngine",
    "OrchestrationEngine",
]
