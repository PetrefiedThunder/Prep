"""In-memory persistence for IoT telemetry."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable, DefaultDict, Iterable, List

from .mqtt.schemas.mqtt.phase2 import MQTTSchema, SensorType

AlertHook = Callable[[MQTTSchema], None]


class TelemetryStorage:
    """Simple storage to persist telemetry and notify alert hooks."""

    def __init__(self) -> None:
        self._records: DefaultDict[SensorType, List[MQTTSchema]] = defaultdict(list)
        self._alert_hooks: DefaultDict[SensorType, List[AlertHook]] = defaultdict(list)

    def persist(self, sensor_type: SensorType, telemetry: MQTTSchema) -> None:
        """Persist telemetry and notify registered alert hooks."""

        self._records[sensor_type].append(telemetry)
        for hook in list(self._alert_hooks[sensor_type]):
            hook(telemetry)

    def history(self, sensor_type: SensorType) -> List[MQTTSchema]:
        """Return historical telemetry for a sensor type."""

        return list(self._records.get(sensor_type, []))

    def register_alert_hook(self, sensor_type: SensorType, hook: AlertHook) -> None:
        """Register a callable to receive telemetry alerts."""

        self._alert_hooks[sensor_type].append(hook)

    def clear_alert_hooks(self, sensor_type: SensorType) -> None:
        """Remove all alert hooks for the provided sensor type."""

        self._alert_hooks.pop(sensor_type, None)

    def registered_sensor_types(self) -> Iterable[SensorType]:
        """Return sensor types with persisted telemetry."""

        return self._records.keys()
