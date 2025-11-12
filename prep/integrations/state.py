"""State store for integration health information."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from .models import (
    IntegrationEvent,
    IntegrationHealth,
    IntegrationHealthSnapshot,
    IntegrationStatus,
)


class IntegrationStatusStore:
    """Thread-safe, asyncio-aware cache of integration status."""

    def __init__(self) -> None:
        self._statuses: dict[str, IntegrationStatus] = {}
        self._lock = asyncio.Lock()

    async def apply_event(self, event: IntegrationEvent) -> IntegrationStatus:
        """Apply an event and return the updated status."""

        async with self._lock:
            status = self._statuses.get(event.integration_id)
            if status is None:
                status = IntegrationStatus(
                    id=event.integration_id,
                    name=event.integration_name,
                    connected=event.payload.get("connected", False),
                )
                self._statuses[event.integration_id] = status
            status.update_from_event(event)
            return status

    async def bulk_replace(self, statuses: Iterable[IntegrationStatus]) -> None:
        """Replace current state with the provided snapshot."""

        async with self._lock:
            self._statuses = {status.id: status for status in statuses}

    async def list_statuses(self) -> list[IntegrationStatus]:
        async with self._lock:
            return [status.model_copy() for status in self._statuses.values()]

    async def health_snapshot(self) -> IntegrationHealthSnapshot:
        async with self._lock:
            total = len(self._statuses)
            healthy = sum(
                1
                for status in self._statuses.values()
                if status.health is IntegrationHealth.HEALTHY
            )
            degraded = sum(
                1
                for status in self._statuses.values()
                if status.health is IntegrationHealth.DEGRADED
            )
            down = sum(
                1 for status in self._statuses.values() if status.health is IntegrationHealth.DOWN
            )
        return IntegrationHealthSnapshot(total=total, healthy=healthy, degraded=degraded, down=down)


integration_status_store = IntegrationStatusStore()

__all__ = ["IntegrationStatusStore", "integration_status_store"]
