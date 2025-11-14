"""Typed models describing integration events and health state."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IntegrationHealth(str, Enum):
    """Enumeration of the supported health states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class IntegrationAuthStatus(str, Enum):
    """Authorization states mirrored from UI expectations."""

    CONNECTED = "connected"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"


class IntegrationEvent(BaseModel):
    """Event emitted when an integration changes state."""

    integration_id: str = Field(..., alias="integrationId")
    integration_name: str = Field(..., alias="integrationName")
    source: str = Field(..., description="Emitter of the event (service name or worker)")
    event_type: str = Field(..., alias="eventType")
    status: str = Field(..., description="High-level status payload")
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }


class IntegrationStatus(BaseModel):
    """Snapshot representing the latest known status for an integration."""

    id: str
    name: str
    description: str | None = None
    connected: bool = False
    auth_status: IntegrationAuthStatus = Field(
        default=IntegrationAuthStatus.PENDING, alias="authStatus"
    )
    last_sync_at: datetime | None = Field(default=None, alias="lastSyncAt")
    health: IntegrationHealth = IntegrationHealth.DEGRADED
    last_event_at: datetime | None = Field(default=None, alias="lastEventAt")
    issues: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }

    def as_frontend_payload(self) -> dict[str, Any]:
        """Return a JSON-ready representation for the frontend."""

        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "connected": self.connected,
            "authStatus": self.auth_status.value,
            "lastSyncAt": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "health": self.health.value,
            "lastEventAt": self.last_event_at.isoformat() if self.last_event_at else None,
            "issues": self.issues,
        }

    def update_from_event(self, event: IntegrationEvent) -> None:
        """Mutate the status in-place based on an incoming event."""

        self.last_event_at = event.occurred_at
        status_payload: Mapping[str, Any] = event.payload
        auth = status_payload.get("auth_status") or status_payload.get("authStatus")
        if auth:
            try:
                self.auth_status = IntegrationAuthStatus(auth)
            except ValueError:
                pass
        health = status_payload.get("health")
        if health:
            try:
                self.health = IntegrationHealth(health)
            except ValueError:
                pass
        if "connected" in status_payload:
            self.connected = bool(status_payload["connected"])
        if "last_sync_at" in status_payload:
            value = status_payload["last_sync_at"]
            self.last_sync_at = _coerce_datetime(value)
        if "lastSyncAt" in status_payload:
            self.last_sync_at = _coerce_datetime(status_payload["lastSyncAt"])
        if "issues" in status_payload:
            self.issues = str(status_payload["issues"]) if status_payload["issues"] else None
        if "description" in status_payload:
            self.description = status_payload["description"]
        metadata = status_payload.get("metadata")
        if isinstance(metadata, MutableMapping):
            self.metadata.update(metadata)


class IntegrationHealthSnapshot(BaseModel):
    """Aggregated metrics for Grafana dashboards."""

    total: int
    healthy: int
    degraded: int
    down: int
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="lastUpdated")

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


__all__ = [
    "IntegrationEvent",
    "IntegrationStatus",
    "IntegrationHealth",
    "IntegrationAuthStatus",
    "IntegrationHealthSnapshot",
]
