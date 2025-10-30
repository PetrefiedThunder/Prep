"""In-memory persistence layer for kitchen metrics synchronized from QSR."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


@dataclass(frozen=True, slots=True)
class KitchenMetric:
    """Normalized kitchen metric durations sourced from external providers."""

    location_id: str
    collected_at: datetime
    prep_duration_seconds: int
    cook_duration_seconds: int
    source: str = "qsr"

    def prep_minutes(self) -> float:
        """Return the preparation duration expressed in minutes."""

        return self.prep_duration_seconds / 60.0

    def cook_minutes(self) -> float:
        """Return the cooking duration expressed in minutes."""

        return self.cook_duration_seconds / 60.0


class KitchenMetricsRepository:
    """Simple in-memory store retaining the most recent metrics per location."""

    def __init__(self) -> None:
        self._records: dict[str, KitchenMetric] = {}

    def save(self, metrics: Iterable[KitchenMetric]) -> list[KitchenMetric]:
        """Persist metrics, keeping the latest reading for each location."""

        order: list[str] = []
        for metric in metrics:
            location_id = metric.location_id
            if location_id not in order:
                order.append(location_id)
            existing = self._records.get(location_id)
            if existing is None or metric.collected_at >= existing.collected_at:
                self._records[location_id] = metric
        return [self._records[location_id] for location_id in order]

    def list_all(self) -> list[KitchenMetric]:
        """Return the latest known metrics for every tracked location."""

        return sorted(self._records.values(), key=lambda metric: (metric.collected_at, metric.location_id))

    def clear(self) -> None:
        """Remove all persisted metrics."""

        self._records.clear()


class KitchenMetricsService:
    """Facade for interacting with kitchen metric storage."""

    def __init__(self, repository: KitchenMetricsRepository | None = None) -> None:
        self._repository = repository or KitchenMetricsRepository()

    @property
    def repository(self) -> KitchenMetricsRepository:
        return self._repository

    def record_metrics(self, metrics: Iterable[KitchenMetric]) -> list[KitchenMetric]:
        """Store metrics and return the persisted representations."""

        return self._repository.save(metrics)

    def get_latest_metrics(self) -> list[KitchenMetric]:
        """Return the latest metrics per location."""

        return self._repository.list_all()

    def reset(self) -> None:
        """Clear all persisted metrics."""

        self._repository.clear()


_default_service = KitchenMetricsService()


def get_default_kitchen_metrics_service() -> KitchenMetricsService:
    """Return a process-wide service instance for convenience callers."""

    return _default_service


__all__ = [
    "KitchenMetric",
    "KitchenMetricsRepository",
    "KitchenMetricsService",
    "get_default_kitchen_metrics_service",
]
