"""Integration smoke tests for regulatory router."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from prep.api.regulatory import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_list_obligations_returns_empty_when_unconfigured() -> None:
    response = client.get("/regulatory/reg/obligations", params={"jurisdiction": "US-CA-LA-County"})
    assert response.status_code == 200
    data = response.json()
    assert data["jurisdiction"] == "US-CA-LA-County"
    assert data["obligations"] == []


def test_evaluate_booking_returns_default_shape() -> None:
    response = client.post("/regulatory/reg/evaluate", json={"subject": "booking"})
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"allowed", "violations", "proofs", "provenance_hash"}


def test_provenance_endpoints_return_placeholders() -> None:
    proof_resp = client.get("/regulatory/reg/proof/test-proof")
    assert proof_resp.status_code == 200
    assert proof_resp.json()["status"] == "unavailable"

    prov_resp = client.get("/regulatory/reg/provenance/test-hash")
    assert prov_resp.status_code == 200
    assert prov_resp.json()["hash"] == "test-hash"
