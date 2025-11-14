"""Audit logging utilities for compliance orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class AuditRecord:
    """Represents a normalized audit log entry."""

    timestamp: datetime
    category: str
    details: dict[str, Any] = field(default_factory=dict)
    user_id: str | None = None
    action_type: str | None = None
    resource: str | None = None
    outcome: str | None = None


class AuditService:
    """Simple in-memory audit service used by the orchestration layer."""

    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    async def record_compliance_check(
        self,
        *,
        domain: Any,
        entity_id: str,
        result: Any,
        schema_version: str | None = None,
        evidence_reference: dict[str, str] | None = None,
    ) -> AuditRecord:
        """Persist an audit record for a compliance check."""

        details = {
            "entity_id": entity_id,
            "domain": getattr(domain, "value", str(domain)),
            "result_summary": getattr(result, "summary", None),
            "overall_compliance": getattr(result, "overall_compliance", None),
            "risk_level": getattr(result, "risk_level", None),
            "schema_version": schema_version,
            "evidence": evidence_reference,
        }

        record = AuditRecord(
            timestamp=datetime.now(UTC),
            category="compliance_check",
            details=details,
        )
        self._records.append(record)
        return record

    async def record_validation_failure(
        self,
        *,
        domain: Any,
        entity_id: str,
        errors: list[str],
    ) -> AuditRecord:
        """Record a validation failure emitted by a compliance engine."""

        record = AuditRecord(
            timestamp=datetime.now(UTC),
            category="compliance_validation_error",
            details={
                "entity_id": entity_id,
                "domain": getattr(domain, "value", str(domain)),
                "errors": errors,
            },
        )
        self._records.append(record)
        return record

    async def list_records(self) -> list[AuditRecord]:
        """Return all audit records recorded so far."""

        return list(self._records)


__all__ = ["AuditRecord", "AuditService"]
