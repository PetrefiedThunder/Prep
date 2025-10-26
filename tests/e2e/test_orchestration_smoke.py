"""End-to-end smoke test for the orchestration engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Mapping

import pytest

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
        self.evidence_requests: list[Iterable[str]] = []

    async def validate_compliance(
        self, entity_data: Mapping[str, Any], jurisdiction: str | None
    ) -> ComplianceResult:
        return self._result

    async def generate_evidence(self, requirements: Iterable[str]) -> List[_StubEvidence]:
        self.evidence_requests.append(list(requirements))
        return [_StubEvidence({"requirements": list(requirements)})]

    async def monitor_changes(self) -> List[Any]:
        return []


@pytest.mark.asyncio
async def test_orchestration_smoke_generates_report_and_audit() -> None:
    orchestrator = OrchestrationEngine()

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

    orchestrator.register_engine(ComplianceDomain.GDPR_CCPA, _StubEngine(gdpr_result))
    orchestrator.register_engine(ComplianceDomain.AML_KYC, _StubEngine(aml_result))

    entity_payload = {
        "id": "42c46fd8-3f8c-42fe-9d6f-2fb3246ab4c4",
        "jurisdiction": "us",
        "customers": ["acme-corp"],
        "consents": ["marketing"],
    }

    report = await orchestrator.orchestrate_compliance_check(
        [ComplianceDomain.GDPR_CCPA, ComplianceDomain.AML_KYC],
        entity_payload,
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
    assert len(audit_records) >= 2
    assert {record.details["domain"] for record in audit_records} == {
        ComplianceDomain.GDPR_CCPA.value,
        ComplianceDomain.AML_KYC.value,
    }
    assert all(record.details["entity_id"] == entity_payload["id"] for record in audit_records)
