from __future__ import annotations

import asyncio
from collections.abc import Iterable, Mapping
from typing import Any

from prep.core.orchestration import ComplianceDomain, ComplianceEngine, OrchestrationEngine


class _InvalidEngine(ComplianceEngine):
    async def validate_compliance(
        self, entity_data: Mapping[str, Any], jurisdiction: str | None
    ) -> Mapping[str, Any]:
        return {"unexpected": True}

    async def generate_evidence(self, requirements: Iterable[str]) -> list[Any]:
        return []

    async def monitor_changes(self) -> list[Any]:
        return []


def test_orchestration_records_validation_error() -> None:
    async def _run() -> None:
        orchestrator = OrchestrationEngine()
        orchestrator.register_engine(ComplianceDomain.GDPR_CCPA, _InvalidEngine())

        report = await orchestrator.orchestrate_compliance_check(
            [ComplianceDomain.GDPR_CCPA],
            {"id": "abc", "jurisdiction": "us"},
        )

        assert report.domain_results == {}
        records = await orchestrator.audit_trail.list_records()
        error_records = [
            record for record in records if record.category == "compliance_validation_error"
        ]
        assert len(error_records) == 1
        assert error_records[0].details["domain"] == ComplianceDomain.GDPR_CCPA.value

    asyncio.run(_run())
