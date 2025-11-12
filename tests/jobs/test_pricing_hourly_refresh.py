from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import pytest

import jobs.pricing_hourly_refresh as pricing_refresh
from jobs.pricing_hourly_refresh import run_pricing_refresh
from prep.monitoring.observability import EnterpriseObservability


@dataclass
class StubKitchen:
    id: str
    hourly_rate: Decimal | None
    trust_score: float | None = None
    pricing: dict[str, Any] | None = field(default_factory=dict)


class StubSession:
    def __init__(self) -> None:
        self.closed = False
        self.rolled_back = False

    def close(self) -> None:
        self.closed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def add(self, kitchen: StubKitchen) -> None:
        pass

    def commit(self) -> None:
        pass


def _session_factory(session: StubSession) -> Callable[[], StubSession]:
    return lambda: session


def test_run_pricing_refresh_updates_kitchens(monkeypatch: pytest.MonkeyPatch):
    kitchen_one = StubKitchen(id="k1", hourly_rate=Decimal("120"), trust_score=0.8)
    kitchen_two = StubKitchen(id="k2", hourly_rate=None)
    kitchens = [kitchen_one, kitchen_two]

    monkeypatch.setattr(pricing_refresh, "_load_refresh_candidates", lambda session: kitchens)

    updated: list[StubKitchen] = []

    def _capture_updates(session: StubSession, models: list[StubKitchen]) -> None:
        updated.extend(models)

    monkeypatch.setattr(pricing_refresh, "_persist_updates", _capture_updates)

    status_payloads: list[dict[str, Any]] = []

    async def _store_status(payload: dict[str, Any]) -> None:
        status_payloads.append(payload)

    monkeypatch.setattr(pricing_refresh, "store_pricing_status", _store_status)

    session = StubSession()
    observability = EnterpriseObservability()

    summary = run_pricing_refresh(
        session_factory=_session_factory(session),
        observability=observability,
    )

    assert summary.processed == 2
    assert summary.updated == 1
    assert summary.skipped == 1
    assert summary.failures == 0
    assert summary.errors == []

    assert "recommended_rate" in kitchen_one.pricing
    assert kitchen_two.pricing == {}
    assert updated == [kitchen_one]

    counters = observability.metrics.counters()
    assert counters.get("jobs.pricing_hourly_refresh.success") == 1
    gauges = observability.metrics.gauges()
    assert "jobs.pricing_hourly_refresh.last_run_timestamp" in gauges

    assert status_payloads
    cached = status_payloads[0]
    assert cached["status"] == "success"
    assert cached["processed"] == 2


def test_beat_schedule_entry_exposes_hourly_metadata():
    entry = pricing_refresh.beat_schedule_entry()
    assert entry["schedule"]["minute"] == "0"
    assert entry["schedule"]["hour"] == "*"
    assert "pricing" in entry["options"]["queue"]
