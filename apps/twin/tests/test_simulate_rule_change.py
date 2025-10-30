"""Tests for digital twin simulation."""
from __future__ import annotations

from fastapi.testclient import TestClient

from apps.twin.main import app


client = TestClient(app)


def test_simulate_returns_metrics() -> None:
    payload = {"obligations": [], "workflow": {}}
    response = client.post("/simulate", json=payload)
    data = response.json()
    assert set(data) == {"time_to_compliance", "affected_steps", "expected_violation_rate"}
