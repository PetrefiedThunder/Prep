import pytest
from prep.core.orchestration import OrchestrationEngine, ComplianceDomain
from prep.compliance.gdpr_ccpa.engine import GDPRCCPAEngine
from prep.compliance.aml_kyc.engine import AMLKYCEngine

@pytest.mark.asyncio
async def test_orchestration_smoke():
    orch = OrchestrationEngine()
    orch.register_engine(ComplianceDomain.GDPR_CCPA, GDPRCCPAEngine())
    orch.register_engine(ComplianceDomain.AML_KYC, AMLKYCEngine())
    entity = {
        "id": "test-1",
        "jurisdiction": "EU",
        "data_inventory": {"users": []},
        "consents": [{"timestamp": "2025-01-01"}]
    }
    report = await orch.orchestrate_compliance_check(
        [ComplianceDomain.GDPR_CCPA, ComplianceDomain.AML_KYC], entity
    )
    assert report.entity_id == "test-1"
    assert report.domain_results
    assert 0.0 <= report.overall_risk_score <= 1.0
