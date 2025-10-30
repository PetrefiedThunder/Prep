"""MQTT consumer wired for Prep phase 2 IoT sensors."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Iterable, Mapping

from .mqtt.schemas.mqtt.phase2 import (
    PHASE2_SCHEMA_REGISTRY,
    PHASE2_TOPICS,
    MQTTSchema,
    SensorType,
    load_telemetry,
)
from .storage import TelemetryStorage

Handler = Callable[[MQTTSchema], None]


class MQTTConsumer:
    """Consumer that subscribes to kitchen sensor topics and dispatches payloads."""

    def __init__(
        self,
        client: Any,
        storage: TelemetryStorage,
        handlers: Mapping[SensorType, Handler] | None = None,
    ) -> None:
        self._client = client
        self._storage = storage
        self._handlers: Dict[SensorType, Handler] = dict(handlers or {})
        self._subscriptions_added = False

    def add_handler(self, sensor_type: SensorType, handler: Handler) -> None:
        self._handlers[sensor_type] = handler

    def subscribe(self) -> None:
        """Subscribe to all known phase 2 topics and register callbacks."""

        if self._subscriptions_added:
            return

        if hasattr(self._client, "on_message"):
            self._client.on_message = self._on_message

        for topic in PHASE2_SCHEMA_REGISTRY.topics():
            self._client.subscribe(topic)
        self._subscriptions_added = True

    # pylint: disable=unused-argument
    def _on_message(self, client: Any, userdata: Any, message: Any) -> None:
        topic = getattr(message, "topic")
        payload_bytes = getattr(message, "payload")
        if isinstance(payload_bytes, bytes):
            raw_payload = payload_bytes.decode("utf-8")
        else:
            raw_payload = payload_bytes

        payload = json.loads(raw_payload)
        telemetry = load_telemetry(topic, payload)
        sensor_type = self._sensor_type_for_topic(topic)
        self._storage.persist(sensor_type, telemetry)

        handler = self._handlers.get(sensor_type)
        if handler is not None:
            handler(telemetry)

    def _sensor_type_for_topic(self, topic: str) -> SensorType:
        for sensor_type, mapped_topic in PHASE2_TOPICS.items():
            if topic == mapped_topic:
                return sensor_type
        raise KeyError(f"Unknown topic received: {topic}")

    def known_topics(self) -> Iterable[str]:
        return tuple(PHASE2_SCHEMA_REGISTRY.topics())


class SimpleMQTTMessage:
    """Utility class used by tests to simulate MQTT messages."""

    def __init__(self, topic: str, payload: str | bytes) -> None:
        self.topic = topic
        self.payload = payload


class TopicAwareClient:
    """Minimal interface for tests to confirm subscriptions."""

    def __init__(self) -> None:
        self.on_message: Callable[[Any, Any, Any], None] | None = None
        self.subscribed: list[str] = []

    def subscribe(self, topic: str) -> None:  # pragma: no cover - simple delegation
        self.subscribed.append(topic)

    # helper for tests
    def emit(self, topic: str, payload: Mapping[str, Any]) -> None:
        if self.on_message is None:
            raise RuntimeError("No message handler configured")
        message = SimpleMQTTMessage(topic, json.dumps(payload).encode("utf-8"))
        self.on_message(self, None, message)
