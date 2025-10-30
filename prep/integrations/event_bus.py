"""Kafka-backed event bus utilities for integration workflows."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable, List, Optional, Protocol

from .models import IntegrationEvent
from .state import IntegrationStatusStore

try:  # pragma: no cover - optional dependency in unit tests
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer  # type: ignore
except Exception:  # pragma: no cover - handled gracefully when Kafka is unavailable
    AIOKafkaConsumer = None  # type: ignore[assignment]
    AIOKafkaProducer = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class IntegrationEventPublisher(Protocol):
    """Protocol for publishing integration events."""

    async def publish(self, event: IntegrationEvent) -> None:  # pragma: no cover - interface definition
        """Publish an :class:`IntegrationEvent`."""


class InMemoryIntegrationEventBus:
    """Simple event bus used for local testing and unit tests."""

    def __init__(self) -> None:
        self._subscribers: List[Callable[[IntegrationEvent], Awaitable[None]]] = []

    def subscribe(self, handler: Callable[[IntegrationEvent], Awaitable[None]]) -> None:
        self._subscribers.append(handler)

    async def publish(self, event: IntegrationEvent) -> None:
        for handler in list(self._subscribers):
            await handler(event)


class KafkaIntegrationEventPublisher:
    """Kafka producer that emits integration events to ``integration_events`` topic."""

    def __init__(
        self,
        *,
        bootstrap_servers: str,
        topic: str = "integration_events",
        client_id: str = "prep-integration-publisher",
    ) -> None:
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.client_id = client_id
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        if AIOKafkaProducer is None:  # pragma: no cover - environment guard
            raise RuntimeError("aiokafka is required to use KafkaIntegrationEventPublisher")
        if self._producer is None:
            producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            )
            await producer.start()
            self._producer = producer
            logger.info(
                "Kafka integration publisher started", topic=self.topic, bootstrap_servers=self.bootstrap_servers
            )

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            logger.info("Kafka integration publisher stopped", topic=self.topic)
            self._producer = None

    async def publish(self, event: IntegrationEvent) -> None:
        if self._producer is None:
            raise RuntimeError("KafkaIntegrationEventPublisher.start() must be awaited before publishing")
        payload = event.model_dump(by_alias=True, mode="json")
        await self._producer.send_and_wait(self.topic, payload)


class KafkaIntegrationEventConsumer:
    """Background consumer that updates the :class:`IntegrationStatusStore`."""

    def __init__(
        self,
        *,
        bootstrap_servers: str,
        store: IntegrationStatusStore,
        topic: str = "integration_events",
        group_id: str = "prep-integration-consumer",
    ) -> None:
        self.bootstrap_servers = bootstrap_servers
        self.store = store
        self.topic = topic
        self.group_id = group_id
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._task: Optional[asyncio.Task[None]] = None
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        if AIOKafkaConsumer is None:  # pragma: no cover - environment guard
            raise RuntimeError("aiokafka is required to use KafkaIntegrationEventConsumer")
        if self._consumer is not None:
            return
        consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
            enable_auto_commit=True,
        )
        await consumer.start()
        self._consumer = consumer
        self._stopping.clear()
        self._task = asyncio.create_task(self._consume())
        logger.info(
            "Kafka integration consumer started", topic=self.topic, bootstrap_servers=self.bootstrap_servers
        )

    async def stop(self) -> None:
        self._stopping.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:  # pragma: no cover - expected during shutdown
                pass
        if self._consumer is not None:
            await self._consumer.stop()
            logger.info("Kafka integration consumer stopped", topic=self.topic)
            self._consumer = None

    async def _consume(self) -> None:
        assert self._consumer is not None
        try:
            async for message in self._consumer:
                if message.value is None:
                    continue
                try:
                    payload = message.value
                    event = IntegrationEvent.model_validate(payload)
                    await self.store.apply_event(event)
                except Exception as exc:  # pragma: no cover - resilience path
                    logger.exception("Failed to process integration event", exc_info=exc)
                if self._stopping.is_set():
                    break
        finally:
            logger.debug("Integration consumer loop exited")


__all__ = [
    "IntegrationEventPublisher",
    "InMemoryIntegrationEventBus",
    "KafkaIntegrationEventPublisher",
    "KafkaIntegrationEventConsumer",
]
