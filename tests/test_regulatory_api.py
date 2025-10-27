"""Tests for the regulatory compliance FastAPI endpoints."""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

import apps.compliance_service.main as compliance_main
from prep.models.db import SessionLocal
from prep.models.orm import COIDocument
from prep.regulatory.ingest_state import store_status


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """Reload the FastAPI module to ensure clean state between tests."""

    module = importlib.reload(compliance_main)
    test_client = TestClient(module.app)
    try:
        yield test_client
    finally:
        test_client.close()


def _headers(role: str) -> dict[str, str]:
    return {"X-User-Role": role}


def test_get_regulatory_status(client: TestClient) -> None:
    response = client.get("/api/v1/regulatory/status", headers=_headers("host"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_status"] in {"on_track", "action_required"}
    assert "score" in payload
    assert "last_updated" in payload


def test_upload_coi_persists_metadata(client: TestClient) -> None:
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    response = client.post(
        "/coi",
        files={"file": ("sample-coi.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["valid"] is True
    expiry = datetime.fromisoformat(payload["expiry_date"])
    assert expiry.tzinfo is not None

    session = SessionLocal()
    try:
        documents = session.query(COIDocument).all()
        assert len(documents) == 1
        document = documents[0]
        assert document.filename == "sample-coi.pdf"
        assert document.valid is True
        assert document.expiry_date is not None
    finally:
        session.query(COIDocument).delete()
        session.commit()
        session.close()


def test_regulatory_document_submission_flow(client: TestClient) -> None:
    docs_response = client.get("/api/v1/regulatory/documents", headers=_headers("host"))
    assert docs_response.status_code == 200
    host_docs = docs_response.json()
    assert host_docs, "Expected at least one host document"
    document_id = host_docs[0]["id"]

    submit_response = client.post(
        "/api/v1/regulatory/documents/submit",
        headers=_headers("host"),
        json={"document_id": document_id, "url": "https://cdn.prep/doc.pdf"},
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "submitted"


def test_compliance_check_runs_engine(client: TestClient) -> None:
    payload = {
        "kitchen_payload": {
            "license_info": {
                "license_number": "LIC-123",
                "status": "active",
                "expiration_date": "2025-01-01",
            },
            "inspection_history": [
                {
                    "inspection_date": "2024-02-01",
                    "overall_score": 95,
                    "violations": [],
                    "establishment_closed": False,
                }
            ],
        }
    }
    response = client.post(
        "/api/v1/regulatory/check",
        headers=_headers("admin"),
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["report"]["engine_version"]


def test_history_endpoint_returns_entries(client: TestClient) -> None:
    response = client.get("/api/v1/regulatory/history", headers=_headers("government"))
    assert response.status_code == 200
    history = response.json()
    assert history["total"] >= len(history["items"])
    assert history["items"]


def test_monitoring_alerts_require_admin(client: TestClient) -> None:
    response = client.post(
        "/api/v1/regulatory/monitoring/alerts",
        headers=_headers("host"),
        json={"severity": "warning", "message": "Test"},
    )
    assert response.status_code == 403

    create_response = client.post(
        "/api/v1/regulatory/monitoring/alerts",
        headers=_headers("admin"),
        json={"severity": "warning", "message": "Test"},
    )
    assert create_response.status_code == 201

    list_response = client.get(
        "/api/v1/regulatory/monitoring/alerts",
        headers=_headers("government"),
    )
    assert list_response.status_code == 200
    assert any(alert["message"] == "Test" for alert in list_response.json())


def test_trigger_monitoring_run(client: TestClient) -> None:
    response = client.post(
        "/api/v1/regulatory/monitoring/run",
        headers=_headers("government"),
        json={"reason": "Scheduled review"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["healthy"] is True
    assert "last_run" in payload


def test_etl_status_endpoint_returns_cached_state(client: TestClient) -> None:
    now = datetime.now(UTC)
    asyncio.run(
        store_status(
            {
                "last_run": now,
                "states_processed": ["CA", "NY"],
                "documents_processed": 5,
                "documents_inserted": 3,
                "documents_updated": 2,
                "documents_changed": 1,
                "failures": ["slow fetch"],
            }
        )
    )

    response = client.get("/etl/status", headers=_headers("admin"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["documents_processed"] == 5
    assert payload["documents_changed"] == 1
    assert payload["states_processed"] == ["CA", "NY"]
    assert payload["failures"] == ["slow fetch"]
