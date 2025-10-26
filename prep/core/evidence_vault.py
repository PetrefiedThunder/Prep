"""Append-only evidence vault with SHA-256 integrity hashing."""

from __future__ import annotations

import json
import hashlib
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from .orchestration import ComplianceDomain


class EvidenceWriteError(RuntimeError):
    """Raised when evidence cannot be written to the vault."""


class EvidenceVault:
    """Persist evidence artifacts using append-only semantics."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = (base_dir or Path.cwd() / ".evidence_vault").resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def store(
        self,
        *,
        entity_id: str,
        domain: ComplianceDomain,
        evidence: Any,
    ) -> Mapping[str, str]:
        """Persist evidence and return a reference descriptor."""

        normalized = self._normalize(evidence)
        payload = {
            "entity_id": entity_id,
            "domain": domain.value,
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "evidence": normalized,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        domain_dir = self.base_dir / domain.value
        domain_dir.mkdir(parents=True, exist_ok=True)
        entity_dir = domain_dir / entity_id
        entity_dir.mkdir(parents=True, exist_ok=True)
        file_path = entity_dir / f"{payload['stored_at'].replace(':', '-')}_{digest}.json"

        try:
            with file_path.open("x", encoding="utf-8") as handle:
                json.dump({**payload, "evidence_hash": digest}, handle, indent=2, sort_keys=True)
        except FileExistsError as exc:  # pragma: no cover - extremely unlikely due to unique name
            raise EvidenceWriteError(f"Evidence file already exists: {file_path}") from exc

        return {"hash": digest, "path": str(file_path)}

    def _normalize(self, evidence: Any) -> Any:
        if is_dataclass(evidence):
            data = asdict(evidence)
            return self._rename_schema_version(data)
        if isinstance(evidence, Mapping):
            normalized: MutableMapping[str, Any] = {}
            for key, value in evidence.items():
                normalized[str(key)] = self._normalize(value)
            return self._rename_schema_version(dict(normalized))
        if isinstance(evidence, (list, tuple, set)):
            return [self._normalize(item) for item in evidence]
        if isinstance(evidence, (str, int, float, bool)) or evidence is None:
            return evidence
        return str(evidence)

    def _rename_schema_version(self, payload: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
        if "schema_version" in payload and "x-schema-version" not in payload:
            payload = dict(payload)
            payload["x-schema-version"] = payload.pop("schema_version")
        return payload


__all__ = ["EvidenceVault", "EvidenceWriteError"]
