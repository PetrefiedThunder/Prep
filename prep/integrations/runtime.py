"""Runtime helpers for wiring integration services into FastAPI."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI

from prep.settings import get_settings

from .event_bus import KafkaIntegrationEventConsumer
from .state import integration_status_store

logger = logging.getLogger(__name__)


def configure_integration_event_consumers(app: FastAPI) -> None:
    """Register startup/shutdown hooks for the Kafka consumer."""

    settings = get_settings()
    bootstrap = settings.kafka_bootstrap_servers
    if not bootstrap:
        logger.info("Kafka bootstrap servers not configured; integration consumer disabled")
        return

    consumer: Optional[KafkaIntegrationEventConsumer] = KafkaIntegrationEventConsumer(
        bootstrap_servers=bootstrap,
        store=integration_status_store,
    )

    @app.on_event("startup")
    async def _start_consumer() -> None:  # pragma: no cover - FastAPI lifecycle
        nonlocal consumer
        if consumer is None:
            return
        try:
            await consumer.start()
        except Exception as exc:  # pragma: no cover - env guard
            logger.warning("Failed to start integration event consumer", exc_info=exc)
            consumer = None

    @app.on_event("shutdown")
    async def _stop_consumer() -> None:  # pragma: no cover - FastAPI lifecycle
        if consumer is not None:
            await consumer.stop()


__all__ = ["configure_integration_event_consumers"]
