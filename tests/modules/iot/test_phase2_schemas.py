from __future__ import annotations

import pytest

from modules.iot.consumer import MQTTConsumer, TopicAwareClient
from modules.iot.mqtt.schemas.mqtt.phase2 import (
    PHASE2_TOPICS,
    CleaningTelemetry,
    FreezerTelemetry,
    MQTTSchema,
    OvenTelemetry,
    SensorType,
    load_telemetry,
)
from modules.iot.storage import TelemetryStorage


@pytest.mark.parametrize(
    "schema_cls, payload",
    [
        (
            OvenTelemetry,
            {
                "sensor_id": "oven-1",
                "timestamp": 1_694_830_000,
                "temperature_c": 220.0,
                "set_point_c": 230.0,
                "mode": "cook",
                "door_open": False,
            },
        ),
        (
            FreezerTelemetry,
            {
                "sensor_id": "freezer-1",
                "timestamp": 1_694_830_000,
                "temperature_c": -10.0,
                "power_status": "on",
                "door_open": False,
                "alarm_active": False,
            },
        ),
        (
            CleaningTelemetry,
            {
                "sensor_id": "clean-1",
                "timestamp": 1_694_830_000,
                "zone": "prep-line",
                "status": "clean",
                "agent_ppm": 120.5,
            },
        ),
    ],
)
def test_schema_round_trip(schema_cls, payload):
    telemetry = schema_cls(**payload)
    serialized = telemetry.model_dump()
    assert serialized == payload


def test_load_telemetry_uses_registry():
    payload = {
        "sensor_id": "oven-2",
        "timestamp": 1_694_830_100,
        "temperature_c": 180.5,
        "set_point_c": 200.0,
        "mode": "preheat",
        "door_open": True,
    }
    topic = PHASE2_TOPICS[SensorType.OVEN]
    result = load_telemetry(topic, payload)
    assert isinstance(result, OvenTelemetry)
    assert result.temperature_c == pytest.approx(180.5)


def test_consumer_persists_and_dispatches_handlers():
    client = TopicAwareClient()
    storage = TelemetryStorage()
    handled: list[MQTTSchema] = []

    def oven_handler(event: MQTTSchema) -> None:
        handled.append(event)

    consumer = MQTTConsumer(client, storage, handlers={SensorType.OVEN: oven_handler})
    consumer.subscribe()

    payload = {
        "sensor_id": "oven-3",
        "timestamp": 1_694_830_200,
        "temperature_c": 150.2,
        "set_point_c": 160.0,
        "mode": "cook",
        "door_open": False,
    }
    client.emit(PHASE2_TOPICS[SensorType.OVEN], payload)

    history = storage.history(SensorType.OVEN)
    assert len(history) == 1
    assert history[0].temperature_c == pytest.approx(150.2)
    assert handled and handled[0] is history[0]


def test_alert_hook_invocation():
    client = TopicAwareClient()
    storage = TelemetryStorage()
    consumer = MQTTConsumer(client, storage)
    consumer.subscribe()

    alerts: list[MQTTSchema] = []
    storage.register_alert_hook(SensorType.CLEANING, alerts.append)

    payload = {
        "sensor_id": "clean-2",
        "timestamp": 1_694_830_300,
        "zone": "sink",
        "status": "dirty",
        "agent_ppm": 15.0,
    }
    client.emit(PHASE2_TOPICS[SensorType.CLEANING], payload)

    assert alerts
    assert alerts[0].zone == "sink"
