"""Tests for the graph service scaffolding."""
from __future__ import annotations

from fastapi.testclient import TestClient

from apps.graph_service.main import app


client = TestClient(app)


def test_upsert_document_roundtrip() -> None:
    payload = {
        "doc_id": "doc-1",
        "jurisdiction": "US-CA-LA-County",
        "title": "Test",
        "version": "v1",
        "published_at": "2024-01-01",
        "sections": [],
    }
    response = client.post("/graph/docs", json=payload)
    assert response.status_code == 200
    assert response.json()["doc_id"] == "doc-1"


def test_get_obligations_filters_by_jurisdiction() -> None:
    app.state.obligations = [
        {"jurisdiction": "US-CA-LA-County", "subject": "host", "type": "obligation"},
        {"jurisdiction": "US-NY-NYC", "subject": "host", "type": "obligation"},
    ]
    response = client.get("/graph/obligations", params={"jurisdiction": "US-CA-LA-County"})
    data = response.json()
    assert len(data) == 1
    assert data[0]["jurisdiction"] == "US-CA-LA-County"
