"""Audit logging utilities for compliance orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class AuditRecord:
    """Represents a normalized audit log entry."""

    timestamp: datetime
    category: str
    details: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    action_type: Optional[str] = None
    resource: Optional[str] = None
    outcome: Optional[str] = None


class AuditService:
    """Simple in-memory audit service used by the orchestration layer."""

    def __init__(self) -> None:
        self._records: List[AuditRecord] = []

    async def record_compliance_check(
        self,
        *,
        domain: Any,
        entity_id: str,
        result: Any,
    ) -> AuditRecord:
        """Persist an audit record for a compliance check."""

        details = {
            "entity_id": entity_id,
            "domain": getattr(domain, "value", str(domain)),
            "result_summary": getattr(result, "summary", None),
            "overall_compliance": getattr(result, "overall_compliance", None),
            "risk_level": getattr(result, "risk_level", None),
        }

        record = AuditRecord(
            timestamp=datetime.now(timezone.utc),
            category="compliance_check",
            details=details,
        )
        self._records.append(record)
        return record

    async def list_records(self) -> List[AuditRecord]:
        """Return all audit records recorded so far."""

        return list(self._records)


__all__ = ["AuditRecord", "AuditService"]
