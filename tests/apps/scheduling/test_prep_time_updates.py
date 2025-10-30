from __future__ import annotations

from datetime import datetime, timedelta, timezone

from apps.scheduling.service import SchedulingService
from integrations.square.webhooks import PrepTimeUpdate


def _update(
    *,
    location_id: str,
    order_id: str,
    prep_seconds: int,
    ready_at: datetime,
    updated_at: datetime,
) -> PrepTimeUpdate:
    return PrepTimeUpdate(
        location_id=location_id,
        order_id=order_id,
        prep_time_seconds=prep_seconds,
        ready_at=ready_at,
        updated_at=updated_at,
    )


def test_ingest_creates_window() -> None:
    service = SchedulingService()
    ready_at = datetime(2024, 5, 11, 16, 0, tzinfo=timezone.utc)
    update = _update(
        location_id="loc-1",
        order_id="order-1",
        prep_seconds=900,
        ready_at=ready_at,
        updated_at=ready_at - timedelta(minutes=5),
    )

    window = service.ingest_prep_time_update(update)

    assert window.start_at == ready_at - timedelta(seconds=900)
    assert window.end_at == ready_at
    windows = service.windows_for("loc-1")
    assert len(windows) == 1
    assert windows[0] == window


def test_overlapping_windows_are_merged() -> None:
    service = SchedulingService()
    ready_at = datetime(2024, 5, 11, 17, 0, tzinfo=timezone.utc)
    first = _update(
        location_id="loc-1",
        order_id="order-1",
        prep_seconds=1200,
        ready_at=ready_at,
        updated_at=ready_at - timedelta(minutes=20),
    )
    second = _update(
        location_id="loc-1",
        order_id="order-2",
        prep_seconds=600,
        ready_at=ready_at + timedelta(minutes=5),
        updated_at=ready_at - timedelta(minutes=10),
    )

    service.ingest_prep_time_update(first)
    service.ingest_prep_time_update(second)

    windows = service.windows_for("loc-1")
    assert len(windows) == 1
    window = windows[0]
    assert window.start_at == ready_at - timedelta(seconds=1200)
    assert window.end_at == (ready_at + timedelta(minutes=5))
    assert {window.order_id for window in service.windows_for("loc-1")} == {"order-2"}


def test_windows_for_missing_location() -> None:
    service = SchedulingService()
    assert service.windows_for("missing") == []
