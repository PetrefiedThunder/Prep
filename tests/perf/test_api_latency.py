"""Performance budget tests that guard key API latency constraints."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from api.index import app
from modules.observability import DEFAULT_TARGETED_ROUTES

PERF_BUDGET_MS = 300

pytestmark = pytest.mark.performance


@pytest.fixture(scope="module")
def test_client() -> TestClient:
    return TestClient(app)


@pytest.mark.parametrize("endpoint", [route for route in DEFAULT_TARGETED_ROUTES if route == "/healthz"])
def test_targeted_endpoint_latency_under_budget(test_client: TestClient, endpoint: str) -> None:
    start = time.perf_counter()
    response = test_client.get(endpoint)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    assert elapsed_ms < PERF_BUDGET_MS, (
        f"Endpoint {endpoint} exceeded latency budget: {elapsed_ms:.2f}ms >= {PERF_BUDGET_MS}ms"
    )
