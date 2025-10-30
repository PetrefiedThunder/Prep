from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from prep.integrations.event_bus import InMemoryIntegrationEventBus
from prep.integrations.models import IntegrationEvent
from prep.integrations.state import IntegrationStatusStore


def test_integration_status_store_updates() -> None:
    async def runner() -> None:
        store = IntegrationStatusStore()
        bus = InMemoryIntegrationEventBus()

        async def handler(event: IntegrationEvent) -> None:
            await store.apply_event(event)

        bus.subscribe(handler)

        event = IntegrationEvent(
            integrationId="crm",
            integrationName="CRM",
            source="test-suite",
            eventType="status",
            status="online",
            payload={
                "connected": True,
                "auth_status": "connected",
                "health": "healthy",
                "last_sync_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        await bus.publish(event)

        statuses = await store.list_statuses()
        assert len(statuses) == 1
        status = statuses[0]
        assert status.connected is True
        assert status.auth_status.value == "connected"
        assert status.health.value == "healthy"

        follow_up = IntegrationEvent(
            integrationId="crm",
            integrationName="CRM",
            source="test-suite",
            eventType="status",
            status="offline",
            payload={
                "connected": False,
                "auth_status": "expired",
                "health": "degraded",
                "issues": "token expired",
            },
        )

        await bus.publish(follow_up)

        statuses = await store.list_statuses()
        assert statuses[0].connected is False
        assert statuses[0].auth_status.value == "expired"
        assert statuses[0].health.value == "degraded"
        assert statuses[0].issues == "token expired"

    asyncio.run(runner())


def test_health_snapshot_counts() -> None:
    async def runner() -> None:
        store = IntegrationStatusStore()

        await store.apply_event(
            IntegrationEvent(
                integrationId="healthy",
                integrationName="Healthy",
                source="test",
                eventType="status",
                status="online",
                payload={"connected": True, "health": "healthy"},
            )
        )
        await store.apply_event(
            IntegrationEvent(
                integrationId="degraded",
                integrationName="Degraded",
                source="test",
                eventType="status",
                status="offline",
                payload={"connected": True, "health": "degraded"},
            )
        )
        await store.apply_event(
            IntegrationEvent(
                integrationId="down",
                integrationName="Down",
                source="test",
                eventType="status",
                status="offline",
                payload={"connected": False, "health": "down"},
            )
        )

        snapshot = await store.health_snapshot()
        assert snapshot.total == 3
        assert snapshot.healthy == 1
        assert snapshot.degraded == 1
        assert snapshot.down == 1

    asyncio.run(runner())
