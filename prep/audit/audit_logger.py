"""
Audit Logging System

Immutable, append-only audit logs for compliance and security.
Tracks all changes to critical entities with before/after state.

Features:
- Immutable audit trail
- Before/after state snapshots
- User attribution
- Compliance-ready exports
"""

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    """Types of auditable actions"""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"  # For sensitive data access
    APPROVE = "approve"
    REJECT = "reject"
    EXPORT = "export"
    LOGIN = "login"
    LOGOUT = "logout"


class AuditEntity(str, Enum):
    """Types of entities that are audited"""

    VENDOR = "vendor"
    FACILITY = "facility"
    BOOKING = "booking"
    PAYMENT = "payment"
    COMPLIANCE_CHECK = "compliance_check"
    USER = "user"
    DOCUMENT = "document"
    LEDGER_ENTRY = "ledger_entry"
    PERMIT = "permit"


class AuditSeverity(str, Enum):
    """Severity levels for audit events"""

    LOW = "low"  # Normal operations
    MEDIUM = "medium"  # Important changes
    HIGH = "high"  # Sensitive data access, financial transactions
    CRITICAL = "critical"  # Security events, compliance failures


class AuditLog(BaseModel):
    """Audit log entry"""

    audit_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Action details
    action: AuditAction
    entity_type: AuditEntity
    entity_id: str
    severity: AuditSeverity = AuditSeverity.LOW

    # User details
    user_id: str | None = None
    user_email: str | None = None
    user_ip: str | None = None
    user_agent: str | None = None

    # State changes
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
    changes: dict[str, Any] | None = None  # Computed diff

    # Additional context
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Compliance
    compliance_relevant: bool = False
    retention_years: int = 7  # Default retention for financial records

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AuditLogger:
    """
    Centralized audit logging service.

    Usage:
        audit = AuditLogger()
        await audit.log_update(
            entity_type=AuditEntity.VENDOR,
            entity_id="vendor-123",
            before_state=old_vendor,
            after_state=new_vendor,
            user_id="user-456",
            reason="Updated business license"
        )
    """

    def __init__(self, storage_backend=None):
        """
        Initialize audit logger.

        Args:
            storage_backend: Storage implementation (database, file, etc.)
        """
        self.storage = storage_backend or DatabaseAuditStorage()

    async def log_create(
        self,
        entity_type: AuditEntity,
        entity_id: str,
        after_state: dict[str, Any],
        user_id: str | None = None,
        user_email: str | None = None,
        reason: str | None = None,
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        **kwargs,
    ) -> AuditLog:
        """Log entity creation"""

        log_entry = AuditLog(
            action=AuditAction.CREATE,
            entity_type=entity_type,
            entity_id=entity_id,
            severity=severity,
            user_id=user_id,
            user_email=user_email,
            before_state=None,
            after_state=after_state,
            reason=reason,
            compliance_relevant=self._is_compliance_relevant(entity_type),
            **kwargs,
        )

        await self.storage.save(log_entry)
        return log_entry

    async def log_update(
        self,
        entity_type: AuditEntity,
        entity_id: str,
        before_state: dict[str, Any],
        after_state: dict[str, Any],
        user_id: str | None = None,
        user_email: str | None = None,
        reason: str | None = None,
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        **kwargs,
    ) -> AuditLog:
        """Log entity update with before/after state"""

        changes = self._compute_diff(before_state, after_state)

        log_entry = AuditLog(
            action=AuditAction.UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            severity=severity,
            user_id=user_id,
            user_email=user_email,
            before_state=before_state,
            after_state=after_state,
            changes=changes,
            reason=reason,
            compliance_relevant=self._is_compliance_relevant(entity_type),
            **kwargs,
        )

        await self.storage.save(log_entry)
        return log_entry

    async def log_delete(
        self,
        entity_type: AuditEntity,
        entity_id: str,
        before_state: dict[str, Any],
        user_id: str | None = None,
        user_email: str | None = None,
        reason: str | None = None,
        severity: AuditSeverity = AuditSeverity.HIGH,
        **kwargs,
    ) -> AuditLog:
        """Log entity deletion (soft or hard delete)"""

        log_entry = AuditLog(
            action=AuditAction.DELETE,
            entity_type=entity_type,
            entity_id=entity_id,
            severity=severity,
            user_id=user_id,
            user_email=user_email,
            before_state=before_state,
            after_state=None,
            reason=reason,
            compliance_relevant=True,  # All deletions are compliance-relevant
            **kwargs,
        )

        await self.storage.save(log_entry)
        return log_entry

    async def log_read(
        self,
        entity_type: AuditEntity,
        entity_id: str,
        user_id: str | None = None,
        user_email: str | None = None,
        severity: AuditSeverity = AuditSeverity.LOW,
        **kwargs,
    ) -> AuditLog:
        """Log sensitive data access (PII, financial data)"""

        log_entry = AuditLog(
            action=AuditAction.READ,
            entity_type=entity_type,
            entity_id=entity_id,
            severity=severity,
            user_id=user_id,
            user_email=user_email,
            compliance_relevant=True,
            **kwargs,
        )

        await self.storage.save(log_entry)
        return log_entry

    async def log_compliance_action(
        self,
        action: AuditAction,
        entity_type: AuditEntity,
        entity_id: str,
        details: dict[str, Any],
        user_id: str | None = None,
        user_email: str | None = None,
        reason: str | None = None,
        **kwargs,
    ) -> AuditLog:
        """Log compliance-related actions (approve, reject, etc.)"""

        log_entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            severity=AuditSeverity.HIGH,
            user_id=user_id,
            user_email=user_email,
            metadata=details,
            reason=reason,
            compliance_relevant=True,
            **kwargs,
        )

        await self.storage.save(log_entry)
        return log_entry

    async def get_entity_history(self, entity_type: AuditEntity, entity_id: str) -> list[AuditLog]:
        """Get full audit history for an entity"""
        return await self.storage.get_by_entity(entity_type, entity_id)

    async def get_user_activity(self, user_id: str) -> list[AuditLog]:
        """Get all activity by a specific user"""
        return await self.storage.get_by_user(user_id)

    async def export_compliance_report(
        self, start_date: datetime, end_date: datetime
    ) -> list[AuditLog]:
        """Export audit logs for compliance reporting"""
        return await self.storage.get_by_date_range(start_date, end_date, compliance_only=True)

    def _compute_diff(self, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
        """Compute diff between before and after states"""

        changes = {}

        # Find modified and added fields
        for key, after_value in after.items():
            before_value = before.get(key)
            if before_value != after_value:
                changes[key] = {"before": before_value, "after": after_value}

        # Find removed fields
        for key in before:
            if key not in after:
                changes[key] = {"before": before[key], "after": None}

        return changes

    def _is_compliance_relevant(self, entity_type: AuditEntity) -> bool:
        """Determine if entity type is compliance-relevant"""

        compliance_entities = {
            AuditEntity.VENDOR,
            AuditEntity.FACILITY,
            AuditEntity.BOOKING,
            AuditEntity.PAYMENT,
            AuditEntity.COMPLIANCE_CHECK,
            AuditEntity.PERMIT,
            AuditEntity.LEDGER_ENTRY,
        }

        return entity_type in compliance_entities


class DatabaseAuditStorage:
    """Database storage backend for audit logs"""

    async def save(self, log_entry: AuditLog):
        """Save audit log to database"""
        # Implementation would insert into audit_logs table
        # For now, just log to stdout
        print(
            f"[AUDIT] {log_entry.action.value} {log_entry.entity_type.value}:{log_entry.entity_id} by {log_entry.user_email or 'system'}"
        )

    async def get_by_entity(self, entity_type: AuditEntity, entity_id: str) -> list[AuditLog]:
        """Get all audit logs for an entity"""
        # SELECT * FROM audit_logs WHERE entity_type = ? AND entity_id = ?
        return []

    async def get_by_user(self, user_id: str) -> list[AuditLog]:
        """Get all audit logs for a user"""
        # SELECT * FROM audit_logs WHERE user_id = ?
        return []

    async def get_by_date_range(
        self, start_date: datetime, end_date: datetime, compliance_only: bool = False
    ) -> list[AuditLog]:
        """Get audit logs within date range"""
        # SELECT * FROM audit_logs WHERE timestamp BETWEEN ? AND ?
        return []


# Decorator for automatic audit logging
def audit_log(
    action: AuditAction,
    entity_type: AuditEntity,
    severity: AuditSeverity = AuditSeverity.MEDIUM,
):
    """
    Decorator to automatically log function calls.

    Usage:
        @audit_log(action=AuditAction.UPDATE, entity_type=AuditEntity.VENDOR)
        async def update_vendor(vendor_id: str, updates: dict, user_id: str):
            # Function implementation
            pass
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract entity_id and user_id from function args/kwargs
            entity_id = (
                kwargs.get("entity_id") or kwargs.get("vendor_id") or kwargs.get("facility_id")
            )
            user_id = kwargs.get("user_id")

            # Execute function
            result = await func(*args, **kwargs)

            # Log audit
            audit = AuditLogger()
            await audit.log_compliance_action(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details={"function": func.__name__, "result": "success"},
                user_id=user_id,
                severity=severity,
            )

            return result

        return wrapper

    return decorator


# Example usage
async def example_usage():
    """Example of audit logging usage"""

    audit = AuditLogger()

    # Log vendor creation
    await audit.log_create(
        entity_type=AuditEntity.VENDOR,
        entity_id="vendor-123",
        after_state={
            "vendor_id": "vendor-123",
            "business_name": "ACME Rentals",
            "status": "active",
        },
        user_id="user-456",
        user_email="admin@prep.com",
        reason="New vendor onboarding",
    )

    # Log vendor update
    await audit.log_update(
        entity_type=AuditEntity.VENDOR,
        entity_id="vendor-123",
        before_state={"business_name": "ACME Rentals", "status": "active"},
        after_state={"business_name": "ACME Short-Term Rentals LLC", "status": "active"},
        user_id="user-456",
        user_email="admin@prep.com",
        reason="Updated business name after LLC formation",
    )

    # Log compliance check
    await audit.log_compliance_action(
        action=AuditAction.APPROVE,
        entity_type=AuditEntity.FACILITY,
        entity_id="facility-789",
        details={"compliance_score": 95, "checks_passed": 12, "checks_failed": 0},
        user_id="user-456",
        user_email="admin@prep.com",
        reason="All compliance requirements met",
    )

    # Get entity history
    history = await audit.get_entity_history(entity_type=AuditEntity.VENDOR, entity_id="vendor-123")
    print(f"Vendor has {len(history)} audit log entries")


if __name__ == "__main__":
    import asyncio

    asyncio.run(example_usage())
