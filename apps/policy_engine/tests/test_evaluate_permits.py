"""Smoke tests for the policy evaluation endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient

from apps.policy_engine.main import app


client = TestClient(app)


def test_evaluate_returns_allowed() -> None:
    payload = {
        "subject": "booking",
        "jurisdiction": "US-CA-LA-County",
        "facts": {},
    }
    response = client.post("/evaluate", json=payload)
    data = response.json()
    assert response.status_code == 200
    assert data["allowed"] is True
