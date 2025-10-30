"""Phase 2 MQTT schemas for kitchen IoT sensors."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Iterable, Mapping, Type, TypeVar

from pydantic import BaseModel, Field, ValidationError, field_validator


class SensorType(str, Enum):
    """Enumeration of supported IoT sensor types."""

    OVEN = "oven"
    FREEZER = "freezer"
    CLEANING = "cleaning"


class MQTTSchema(BaseModel):
    """Base schema for MQTT payloads."""

    sensor_id: str = Field(description="Unique identifier for the sensor.")
    timestamp: int = Field(description="Unix timestamp (seconds) when the telemetry was recorded.")

    @field_validator("timestamp")
    @classmethod
    def _validate_timestamp(cls, value: int) -> int:
        if value < 0:
            msg = "timestamp must be a non-negative unix timestamp"
            raise ValueError(msg)
        return value


class OvenTelemetry(MQTTSchema):
    """Payload produced by connected ovens."""

    temperature_c: float = Field(description="Current temperature of the oven in Celsius.")
    set_point_c: float = Field(description="Configured set point in Celsius.")
    mode: str = Field(description="Current operating mode of the oven.")
    door_open: bool = Field(description="Whether the oven door is open.")

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, value: str) -> str:
        allowed = {"preheat", "cook", "idle", "off"}
        if value not in allowed:
            msg = f"mode must be one of {sorted(allowed)}"
            raise ValueError(msg)
        return value


class FreezerTelemetry(MQTTSchema):
    """Payload produced by connected freezers."""

    temperature_c: float = Field(description="Current temperature of the freezer in Celsius.")
    power_status: str = Field(description="Current power status of the freezer.")
    door_open: bool = Field(description="Whether the freezer door is open.")
    alarm_active: bool = Field(description="Whether the freezer alarm is currently active.")

    @field_validator("power_status")
    @classmethod
    def _validate_power_status(cls, value: str) -> str:
        allowed = {"on", "backup", "off"}
        if value not in allowed:
            msg = f"power_status must be one of {sorted(allowed)}"
            raise ValueError(msg)
        return value


class CleaningTelemetry(MQTTSchema):
    """Payload produced by cleaning sensors."""

    zone: str = Field(description="Kitchen zone where the cleaning sensor is located.")
    status: str = Field(description="Current cleanliness status reported by the sensor.")
    agent_ppm: float = Field(description="Detected cleaning agent concentration in ppm.")

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        allowed = {"clean", "dirty", "in_progress"}
        if value not in allowed:
            msg = f"status must be one of {sorted(allowed)}"
            raise ValueError(msg)
        return value


SchemaType = TypeVar("SchemaType", bound=MQTTSchema)


class SchemaRegistry:
    """Registry that maps MQTT topics to telemetry schemas."""

    def __init__(self, mapping: Mapping[str, Type[SchemaType]]) -> None:
        self._mapping = dict(mapping)

    def topics(self) -> Iterable[str]:
        return self._mapping.keys()

    def schema_for_topic(self, topic: str) -> Type[SchemaType]:
        try:
            return self._mapping[topic]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise KeyError(f"No schema registered for topic '{topic}'") from exc

    def parse(self, topic: str, payload: Mapping[str, Any] | str | bytes) -> MQTTSchema:
        schema_cls = self.schema_for_topic(topic)
        if isinstance(payload, (str, bytes)):
            raise TypeError("payload must be a mapping (decoded JSON dictionary)")
        return schema_cls.model_validate(payload)


PHASE2_TOPICS: Dict[SensorType, str] = {
    SensorType.OVEN: "prep/kitchen/ovens/telemetry",
    SensorType.FREEZER: "prep/kitchen/freezers/telemetry",
    SensorType.CLEANING: "prep/kitchen/cleaning/telemetry",
}


PHASE2_SCHEMA_REGISTRY = SchemaRegistry(
    {
        PHASE2_TOPICS[SensorType.OVEN]: OvenTelemetry,
        PHASE2_TOPICS[SensorType.FREEZER]: FreezerTelemetry,
        PHASE2_TOPICS[SensorType.CLEANING]: CleaningTelemetry,
    }
)


def load_telemetry(topic: str, payload: Mapping[str, Any]) -> MQTTSchema:
    """Convenience helper that parses MQTT payloads using the phase 2 registry."""

    try:
        return PHASE2_SCHEMA_REGISTRY.parse(topic, payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid payload for topic '{topic}': {exc}") from exc
