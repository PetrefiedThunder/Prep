"""Utilities for recalculating scheduling dashboards from kitchen metrics."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence, TYPE_CHECKING

from modules.kitchen_metrics.models import KitchenMetric

if TYPE_CHECKING:  # pragma: no cover - imported for type checkers only
    from modules.kitchen_metrics.models import KitchenMetricsService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SchedulingMetricSnapshot:
    """Represents a scheduling view derived from kitchen metrics."""

    location_id: str
    prep_minutes: float
    cook_minutes: float
    collected_at: datetime


def build_scheduling_snapshots(metrics: Iterable[KitchenMetric]) -> list[SchedulingMetricSnapshot]:
    """Create dashboard snapshots from normalized kitchen metrics."""

    snapshots: list[SchedulingMetricSnapshot] = []
    for metric in metrics:
        snapshots.append(
            SchedulingMetricSnapshot(
                location_id=metric.location_id,
                prep_minutes=metric.prep_minutes(),
                cook_minutes=metric.cook_minutes(),
                collected_at=metric.collected_at,
            )
        )
    snapshots.sort(key=lambda snapshot: (snapshot.collected_at, snapshot.location_id))
    return snapshots


def trigger_scheduling_recalculation(
    service: "KitchenMetricsService",
    *,
    metrics: Sequence[KitchenMetric] | None = None,
) -> list[SchedulingMetricSnapshot]:
    """Recompute scheduling dashboards using the latest kitchen metrics."""

    if metrics is None:
        metrics = service.get_latest_metrics()
    snapshots = build_scheduling_snapshots(metrics)
    logger.info(
        "Scheduling dashboards refreshed from kitchen metrics",
        extra={"locations": len(snapshots)},
    )
    return snapshots


__all__ = [
    "SchedulingMetricSnapshot",
    "build_scheduling_snapshots",
    "trigger_scheduling_recalculation",
]
