"""End-to-end smoke test for the orchestration engine."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from prep.core.evidence_vault import EvidenceVault
from prep.core.orchestration import (
    ComplianceDomain,
    ComplianceEngine,
    ComplianceResult,
    OrchestrationEngine,
    UnifiedComplianceReport,
)


@dataclass
class _StubEvidence:
    items: Mapping[str, Any]


class _StubEngine(ComplianceEngine):
    def __init__(self, result: ComplianceResult) -> None:
        self._result = result
        self.evidence_requests: list[list[str]] = []

    async def validate_compliance(
        self, entity_data: Mapping[str, Any], jurisdiction: str | None
    ) -> ComplianceResult:
        return self._result

    async def generate_evidence(self, requirements: Iterable[str]) -> list[_StubEvidence]:
        captured = list(requirements)
        self.evidence_requests.append(captured)
        return [_StubEvidence({"requirements": captured, "schema_version": "stub-evidence.v1"})]

    async def monitor_changes(self) -> list[Any]:
        return []


def test_orchestration_smoke_generates_report_and_audit() -> None:
    async def _run(evidence_dir: Path) -> None:
        orchestrator = OrchestrationEngine(evidence_vault=EvidenceVault(base_dir=evidence_dir))

        gdpr_result = ComplianceResult(
            domain=ComplianceDomain.GDPR_CCPA,
            is_compliant=True,
            score=0.82,
            issues=["cookie-consent-expired"],
            metadata={"jurisdiction": "eu"},
        )
        aml_result = ComplianceResult(
            domain=ComplianceDomain.AML_KYC,
            is_compliant=False,
            score=0.45,
            issues=["customer-risk-high"],
            metadata={"jurisdiction": "us"},
        )

        gdpr_engine = _StubEngine(gdpr_result)
        aml_engine = _StubEngine(aml_result)

        orchestrator.register_engine(ComplianceDomain.GDPR_CCPA, gdpr_engine)
        orchestrator.register_engine(ComplianceDomain.AML_KYC, aml_engine)

        entity_payload = {
            "id": "42c46fd8-3f8c-42fe-9d6f-2fb3246ab4c4",
            "jurisdiction": "us",
            "customers": ["acme-corp"],
            "consents": ["marketing"],
        }

        report = await orchestrator.orchestrate_compliance_check(
            [ComplianceDomain.GDPR_CCPA, ComplianceDomain.AML_KYC],
            entity_payload,
            evidence_requirements={
                ComplianceDomain.GDPR_CCPA: ["data_mapping"],
                ComplianceDomain.AML_KYC: ["customer_due_diligence"],
            },
        )

        assert isinstance(report, UnifiedComplianceReport)
        assert report.entity_id == entity_payload["id"]
        assert set(report.domain_results.keys()) == {
            ComplianceDomain.GDPR_CCPA,
            ComplianceDomain.AML_KYC,
        }
        assert report.domain_results[ComplianceDomain.GDPR_CCPA] == gdpr_result
        assert report.domain_results[ComplianceDomain.AML_KYC] == aml_result
        assert 0.0 <= report.overall_risk_score <= 1.0

        audit_records = await orchestrator.audit_trail.list_records()
        compliance_records = [
            record for record in audit_records if record.category == "compliance_check"
        ]
        assert len(compliance_records) == 2
        assert {record.details["domain"] for record in compliance_records} == {
            ComplianceDomain.GDPR_CCPA.value,
            ComplianceDomain.AML_KYC.value,
        }
        assert all(
            record.details["entity_id"] == entity_payload["id"] for record in compliance_records
        )
        assert {record.details["schema_version"] for record in compliance_records} == {
            "privacy-compliance.v1",
            "aml-compliance.v1",
        }
        evidence_refs = [record.details["evidence"] for record in compliance_records]
        assert all(ref and Path(ref["path"]).exists() for ref in evidence_refs)
        assert gdpr_engine.evidence_requests == [["data_mapping"]]
        assert aml_engine.evidence_requests == [["customer_due_diligence"]]

    with TemporaryDirectory() as tmp_dir:
        asyncio.run(_run(Path(tmp_dir)))
