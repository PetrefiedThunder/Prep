"""Periodic worker that publishes integration health to Kafka."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from prep.integrations.event_bus import (
    InMemoryIntegrationEventBus,
    IntegrationEventPublisher,
    KafkaIntegrationEventPublisher,
)
from prep.integrations.models import IntegrationEvent, IntegrationHealth
from prep.settings import IntegrationEndpoint, get_settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PingResult:
    integration: IntegrationEndpoint
    healthy: bool
    latency_ms: float
    status_code: int | None
    error: str | None


class IntegrationHealthMonitor:
    """Ping configured integrations and publish health events."""

    def __init__(
        self,
        *,
        endpoints: Sequence[IntegrationEndpoint],
        publisher: IntegrationEventPublisher,
        timeout_seconds: float = 10.0,
        source: str = "integration-health-worker",
    ) -> None:
        self._endpoints = list(endpoints)
        self._publisher = publisher
        self._timeout = timeout_seconds
        self._source = source

    async def ping(self, endpoint: IntegrationEndpoint) -> PingResult:
        """Ping a single endpoint and return the result."""

        start = time.perf_counter()
        status_code: int | None = None
        error: str | None = None
        healthy = False
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.get(str(endpoint.url))
                status_code = response.status_code
                healthy = 200 <= response.status_code < 300
            except httpx.HTTPError as exc:  # pragma: no cover - network failure path
                error = str(exc)
        latency_ms = (time.perf_counter() - start) * 1000
        return PingResult(
            integration=endpoint,
            healthy=healthy,
            latency_ms=latency_ms,
            status_code=status_code,
            error=error,
        )

    async def run_once(self) -> Iterable[PingResult]:
        """Run a single health check cycle and publish results."""

        results: list[PingResult] = []
        for endpoint in self._endpoints:
            result = await self.ping(endpoint)
            results.append(result)
            await self._publisher.publish(self._build_event(result))
        return results

    async def run_forever(self, interval_seconds: float = 300.0) -> None:
        """Continuously run health checks at the provided interval."""

        logger.info("Integration health monitor starting", interval_seconds=interval_seconds)
        while True:
            await self.run_once()
            await asyncio.sleep(interval_seconds)

    def _build_event(self, result: PingResult) -> IntegrationEvent:
        health = IntegrationHealth.HEALTHY if result.healthy else IntegrationHealth.DOWN
        if not result.healthy and result.status_code and 500 <= result.status_code < 600:
            health = IntegrationHealth.DEGRADED
        now = datetime.now(UTC)
        payload = {
            "connected": result.healthy,
            "health": health.value,
            "auth_status": "connected" if result.healthy else "pending",
            "last_sync_at": now.isoformat(),
            "issues": result.error,
            "metadata": {
                "latency_ms": round(result.latency_ms, 2),
                "status_code": result.status_code,
            },
        }
        status = "online" if result.healthy else "offline"
        return IntegrationEvent(
            integrationId=result.integration.id,
            integrationName=result.integration.name,
            source=self._source,
            eventType="health",
            status=status,
            payload=payload,
            occurred_at=now,
        )


async def build_default_monitor(
    publisher: IntegrationEventPublisher | None = None,
) -> IntegrationHealthMonitor:
    """Construct a monitor based on environment configuration."""

    settings = get_settings()
    endpoints = settings.integration_endpoints
    timeout = settings.integration_health_timeout_seconds
    if publisher is None:
        if settings.kafka_bootstrap_servers:
            kafka_publisher = KafkaIntegrationEventPublisher(
                bootstrap_servers=settings.kafka_bootstrap_servers
            )
            try:
                await kafka_publisher.start()
                publisher = kafka_publisher
            except Exception as exc:  # pragma: no cover - graceful degradation
                logger.warning(
                    "Failed to initialize Kafka publisher; falling back to in-memory bus",
                    exc_info=exc,
                )
        if publisher is None:
            publisher = InMemoryIntegrationEventBus()
    return IntegrationHealthMonitor(
        endpoints=endpoints, publisher=publisher, timeout_seconds=timeout
    )


async def main() -> None:  # pragma: no cover - manual execution entrypoint
    settings = get_settings()
    if not settings.integration_endpoints:
        logger.warning("No integration endpoints configured; exiting")
        return
    logger.info(
        "Starting integration health monitor", endpoints=len(settings.integration_endpoints)
    )
    monitor = await build_default_monitor()
    await monitor.run_forever(interval_seconds=300)


if __name__ == "__main__":  # pragma: no cover - script entry
    asyncio.run(main())


__all__ = ["IntegrationHealthMonitor", "build_default_monitor", "PingResult"]
