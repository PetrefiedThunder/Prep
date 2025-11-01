"""Tests for the Prep webhook FastAPI application."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from webhooks.server import main


def _build_signature(secret: str, timestamp: str, payload: bytes) -> str:
    message = f"{timestamp}.".encode("utf-8") + payload
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def set_webhook_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PREP_WEBHOOK_SECRET", "test-secret")
    monkeypatch.delenv("PREP_WEBHOOK_MAX_SKEW_SECONDS", raising=False)
    main._load_settings.cache_clear()  # type: ignore[attr-defined]


def _post_event(
    client: TestClient,
    *,
    payload: dict[str, Any],
    timestamp: datetime | None = None,
    signature: str | None = None,
    event_id: str = "evt_123",
) -> Any:
    body = json.dumps(payload).encode("utf-8")
    ts = timestamp or datetime.now(tz=UTC)
    header_ts = str(int(ts.timestamp()))
    headers = {
        "Prep-Timestamp": header_ts,
        "Prep-Event-Id": event_id,
        "Content-Type": "application/json",
    }

    if signature is None:
        signature = _build_signature("test-secret", header_ts, body)

    headers["Prep-Signature"] = signature
    return client.post("/webhooks/prep", headers=headers, content=body)


def test_webhook_success() -> None:
    client = TestClient(main.app)

    response = _post_event(
        client,
        payload={
            "type": "fees.updated",
            "data": {"fee": "renewal", "city": "oakland"},
        },
        event_id="evt_success",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "accepted"
    assert payload["eventId"] == "evt_success"
    assert payload["details"]["fee_items"] == 2


def test_webhook_rejects_invalid_signature() -> None:
    client = TestClient(main.app)

    response = _post_event(
        client,
        payload={"type": "fees.updated", "data": {}},
        signature="not-valid",
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Prep-Signature header"


def test_webhook_rejects_unhandled_event_type() -> None:
    client = TestClient(main.app)

    response = _post_event(
        client,
        payload={"type": "something.new", "data": {}},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unhandled event type: something.new"


def test_webhook_rejects_payload_without_required_fields() -> None:
    client = TestClient(main.app)

    body = b"{not-json}"
    timestamp = str(int(time.time()))
    response = client.post(
        "/webhooks/prep",
        headers={
            "Prep-Signature": _build_signature("test-secret", timestamp, body),
            "Prep-Timestamp": timestamp,
            "Prep-Event-Id": "evt_invalid",
        },
        content=body,
    )

    assert response.status_code == 422


def test_webhook_rejects_timestamp_outside_skew(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PREP_WEBHOOK_MAX_SKEW_SECONDS", "60")
    main._load_settings.cache_clear()  # type: ignore[attr-defined]

    client = TestClient(main.app)
    too_old = datetime.now(tz=UTC) - timedelta(minutes=30)
    response = _post_event(
        client,
        payload={"type": "fees.updated", "data": {}},
        timestamp=too_old,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Prep-Timestamp outside of allowed skew"


def test_missing_secret_results_in_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PREP_WEBHOOK_SECRET", raising=False)
    main._load_settings.cache_clear()  # type: ignore[attr-defined]

    client = TestClient(main.app)
    response = client.get("/healthz")
    assert response.status_code == 200

    response = client.post(
        "/webhooks/prep",
        headers={
            "Prep-Signature": "unused",
            "Prep-Timestamp": str(int(time.time())),
            "Prep-Event-Id": "evt_missing_secret",
        },
        content=json.dumps({"type": "fees.updated"}),
    )

    assert response.status_code == 500
    assert response.json()["error"] == "webhook receiver misconfigured"
