from __future__ import annotations

import json
import time
from importlib import import_module, reload

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def webhook_module(monkeypatch):
    monkeypatch.setenv("PREP_WEBHOOK_SECRET", "test_secret")
    monkeypatch.delenv("PREP_WEBHOOK_MAX_SKEW", raising=False)
    module = import_module("webhooks.server.main")
    module.get_settings.cache_clear()
    module = reload(module)
    module.get_settings.cache_clear()
    try:
        yield module
    finally:
        module.get_settings.cache_clear()


@pytest.fixture
def client(webhook_module):
    with TestClient(webhook_module.app) as test_client:
        yield test_client


def _sign_payload(module, payload: dict, timestamp: int) -> tuple[bytes, str]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = module.compute_signature("test_secret", str(timestamp), body)
    header = f"t={timestamp},v1={signature}"
    return body, header


def test_fees_updated_success(client, webhook_module):
    timestamp = int(time.time())
    payload = {"id": "evt_123", "type": "fees.updated", "data": {"total_due": "100.00"}}
    body, header = _sign_payload(webhook_module, payload, timestamp)

    response = client.post(
        "/webhooks/fees.updated",
        content=body,
        headers={
            "content-type": "application/json",
            webhook_module.SIGNATURE_HEADER: header,
        },
    )

    assert response.status_code == 200
    assert response.json()["event"] == "fees.updated"
    assert response.json()["id"] == "evt_123"


def test_signature_missing(client):
    payload = {"id": "evt_456", "type": "requirements.updated"}
    response = client.post(
        "/webhooks/requirements.updated",
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing signature header"


def test_signature_mismatch(client, webhook_module):
    timestamp = int(time.time())
    payload = {"id": "evt_789", "type": "policy.decision", "data": {}}
    body, _ = _sign_payload(webhook_module, payload, timestamp)

    response = client.post(
        "/webhooks/policy.decision",
        content=body,
        headers={
            "content-type": "application/json",
            webhook_module.SIGNATURE_HEADER: f"t={timestamp},v1=deadbeef",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid signature"


def test_timestamp_skew(client, webhook_module):
    skewed_timestamp = int(time.time()) - 3600
    payload = {"id": "evt_skew", "type": "fees.updated", "data": {}}
    body, header = _sign_payload(webhook_module, payload, skewed_timestamp)

    response = client.post(
        "/webhooks/fees.updated",
        content=body,
        headers={
            "content-type": "application/json",
            webhook_module.SIGNATURE_HEADER: header,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Signature timestamp is outside the accepted window"


def test_event_type_mismatch(client, webhook_module):
    timestamp = int(time.time())
    payload = {"id": "evt_wrong", "type": "fees.updated"}
    body, header = _sign_payload(webhook_module, payload, timestamp)

    response = client.post(
        "/webhooks/policy.decision",
        content=body,
        headers={
            "content-type": "application/json",
            webhook_module.SIGNATURE_HEADER: header,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unexpected event type"


def test_missing_secret_configuration(monkeypatch):
    monkeypatch.delenv("PREP_WEBHOOK_SECRET", raising=False)
    module = import_module("webhooks.server.main")
    module.get_settings.cache_clear()
    module = reload(module)
    module.get_settings.cache_clear()

    with TestClient(module.app) as client:
        response = client.post("/webhooks/fees.updated", json={"type": "fees.updated"})

    assert response.status_code == 500
    assert response.json()["detail"] == "Webhook server misconfigured"
