from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from apps.scheduling.service import SchedulingService
from integrations.square.webhooks import SquareWebhookVerifier


def _build_payload(ready_at: datetime, updated_at: datetime) -> dict[str, object]:
    return {
        "merchant_id": "merchant-1",
        "location_id": "loc-1",
        "type": "prep_time.updated",
        "data": {
            "id": "order-123",
            "type": "order",
            "object": {
                "prep_time": {
                    "order_id": "order-123",
                    "duration_seconds": 600,
                    "ready_at": ready_at.isoformat().replace("+00:00", "Z"),
                    "updated_at": updated_at.isoformat().replace("+00:00", "Z"),
                }
            },
        },
    }


def _make_app(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, SchedulingService, str]:
    from api.index import create_app
    from api.webhooks.square_kds import get_scheduling_service

    signature_key = "super-secret"
    callback_url = "https://example.com/api/webhooks/square-kds/prep-time"

    monkeypatch.setenv("SQUARE_KDS_SIGNATURE_KEY", signature_key)
    monkeypatch.setenv("SQUARE_KDS_NOTIFICATION_URL", callback_url)

    app = create_app()
    service = SchedulingService()
    app.dependency_overrides[get_scheduling_service] = lambda: service

    return app, service, callback_url


def test_prep_time_webhook_updates_schedule(monkeypatch: pytest.MonkeyPatch) -> None:
    ready_at = datetime(2024, 5, 10, 12, 0, tzinfo=timezone.utc)
    updated_at = ready_at - timedelta(minutes=15)
    payload = _build_payload(ready_at, updated_at)
    body = json.dumps(payload).encode()

    app, service, callback_url = _make_app(monkeypatch)
    verifier = SquareWebhookVerifier("super-secret", callback_url)
    signature = verifier.compute_signature(body)

    with TestClient(app) as client:
        response = client.post(
            "/api/webhooks/square-kds/prep-time",
            data=body,
            headers={
                "content-type": "application/json",
                "x-square-signature": signature,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == "order-123"
    assert data["prep_time_seconds"] == 600
    windows = service.windows_for("loc-1")
    assert len(windows) == 1
    window = windows[0]
    assert window.start_at == ready_at - timedelta(seconds=600)
    assert window.end_at == ready_at


def test_invalid_signature_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    ready_at = datetime(2024, 6, 1, 18, 30, tzinfo=timezone.utc)
    updated_at = ready_at - timedelta(minutes=20)
    payload = _build_payload(ready_at, updated_at)
    body = json.dumps(payload).encode()

    app, _service, _callback_url = _make_app(monkeypatch)

    with TestClient(app) as client:
        response = client.post(
            "/api/webhooks/square-kds/prep-time",
            data=body,
            headers={
                "content-type": "application/json",
                "x-square-signature": "bad",
            },
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Signature mismatch"
