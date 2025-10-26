from __future__ import annotations

from pathlib import Path

from prep.core.evidence_vault import EvidenceVault
from prep.core.orchestration import ComplianceDomain


def test_evidence_vault_writes_hash_and_path(tmp_path: Path) -> None:
    vault = EvidenceVault(base_dir=tmp_path)
    evidence = {"report": "sample", "schema_version": "test.v1"}

    reference = vault.store(
        entity_id="entity-1",
        domain=ComplianceDomain.GDPR_CCPA,
        evidence=evidence,
    )

    stored_path = Path(reference["path"])
    assert stored_path.exists()
    assert reference["hash"]


def test_evidence_vault_normalizes_dataclasses(tmp_path: Path) -> None:
    from dataclasses import dataclass

    @dataclass
    class _Evidence:
        schema_version: str = "evidence.v1"
        detail: str = "ok"

    vault = EvidenceVault(base_dir=tmp_path)
    reference = vault.store(
        entity_id="entity-2",
        domain=ComplianceDomain.AML_KYC,
        evidence=[_Evidence()],
    )

    stored_path = Path(reference["path"])
    contents = stored_path.read_text(encoding="utf-8")
    assert "x-schema-version" in contents
