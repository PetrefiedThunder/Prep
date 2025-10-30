from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from apps.scheduling.metrics import build_scheduling_snapshots
from jobs.qsr_automations_sync import normalize_qsr_metrics, sync_qsr_automations_metrics
from modules.kitchen_metrics.models import KitchenMetricsRepository, KitchenMetricsService


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def test_sync_qsr_metrics_persists_and_triggers(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
    payload = [
        {
            "location_id": "kitchen-1",
            "prep_duration_seconds": 420,
            "cook_duration_seconds": 900,
            "timestamp": _iso(now - timedelta(minutes=10)),
        },
        {
            "location_id": "kitchen-1",
            "prep_duration_seconds": 480,
            "cook_duration_seconds": 960,
            "timestamp": _iso(now),
        },
        {
            "locationId": "kitchen-2",
            "prepSeconds": 600,
            "cookSeconds": 1200,
            "updated_at": _iso(now - timedelta(minutes=5)),
        },
    ]

    repository = KitchenMetricsRepository()
    service = KitchenMetricsService(repository=repository)

    def fake_fetcher() -> list[dict[str, object]]:
        return payload

    recalculations: list[list] = []

    def fake_trigger(service_arg, *, metrics):
        snapshots = build_scheduling_snapshots(metrics)
        recalculations.append(snapshots)
        return snapshots

    monkeypatch.setattr(
        "jobs.qsr_automations_sync.trigger_scheduling_recalculation",
        fake_trigger,
    )

    persisted = sync_qsr_automations_metrics(fetcher=fake_fetcher, service=service)

    assert len(persisted) == 2
    latest_metrics = service.get_latest_metrics()
    assert {metric.location_id for metric in latest_metrics} == {"kitchen-1", "kitchen-2"}
    kitchen1 = next(metric for metric in latest_metrics if metric.location_id == "kitchen-1")
    assert kitchen1.prep_duration_seconds == 480
    assert kitchen1.cook_duration_seconds == 960

    assert recalculations, "Scheduling recalculations should have been triggered"
    snapshots = recalculations[0]
    assert {snapshot.location_id for snapshot in snapshots} == {"kitchen-1", "kitchen-2"}
    assert pytest.approx(next(s.prep_minutes for s in snapshots if s.location_id == "kitchen-2"), 0.01) == 10


def test_normalize_qsr_metrics_skips_invalid_entries() -> None:
    payload = [
        {
            "location_id": "kitchen-3",
            "prep_time_seconds": "300",
            "cook_time_seconds": "900",
            "reported_at": "2024-06-01T12:00:00Z",
        },
        {"cook_duration_seconds": 120},
    ]

    metrics = normalize_qsr_metrics(payload)

    assert len(metrics) == 1
    metric = metrics[0]
    assert metric.location_id == "kitchen-3"
    assert metric.prep_duration_seconds == 300
    assert metric.cook_duration_seconds == 900
    assert metric.collected_at.tzinfo is timezone.utc
