from __future__ import annotations

import asyncio

import pytest

from jobs.integration_health_worker import IntegrationHealthMonitor, PingResult
from prep.integrations.models import IntegrationEvent
from prep.settings import IntegrationEndpoint


class DummyPublisher:
    def __init__(self) -> None:
        self.events: list[IntegrationEvent] = []

    async def publish(self, event: IntegrationEvent) -> None:
        self.events.append(event)


def test_monitor_publishes_events(monkeypatch: pytest.MonkeyPatch) -> None:
    async def runner() -> None:
        endpoint = IntegrationEndpoint.model_validate(
            {"id": "crm", "name": "CRM", "url": "https://example.com/health"}
        )
        publisher = DummyPublisher()
        monitor = IntegrationHealthMonitor(
            endpoints=[endpoint], publisher=publisher, timeout_seconds=0.1
        )

        async def fake_ping(_: IntegrationEndpoint) -> PingResult:
            return PingResult(
                integration=endpoint, healthy=True, latency_ms=12.3, status_code=200, error=None
            )

        monkeypatch.setattr(monitor, "ping", fake_ping)

        await monitor.run_once()

        assert len(publisher.events) == 1
        event = publisher.events[0]
        assert event.integration_id == "crm"
        assert event.payload["connected"] is True
        assert event.payload["health"] == "healthy"
        assert event.status == "online"

    asyncio.run(runner())


def test_monitor_marks_degraded(monkeypatch: pytest.MonkeyPatch) -> None:
    async def runner() -> None:
        endpoint = IntegrationEndpoint.model_validate(
            {"id": "billing", "name": "Billing", "url": "https://billing.example.com/status"}
        )
        publisher = DummyPublisher()
        monitor = IntegrationHealthMonitor(
            endpoints=[endpoint], publisher=publisher, timeout_seconds=0.1
        )

        async def fake_ping(_: IntegrationEndpoint) -> PingResult:
            return PingResult(
                integration=endpoint,
                healthy=False,
                latency_ms=45.6,
                status_code=503,
                error="service unavailable",
            )

        monkeypatch.setattr(monitor, "ping", fake_ping)

        await monitor.run_once()

        assert len(publisher.events) == 1
        event = publisher.events[0]
        assert event.payload["connected"] is False
        assert event.payload["health"] == "degraded"
        assert event.payload["issues"] == "service unavailable"

    asyncio.run(runner())
