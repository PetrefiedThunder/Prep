"""Tests for the regulatory compliance FastAPI endpoints."""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import apps.compliance_service.main as compliance_main
import prep.compliance.coi_validator as coi_validator
from prep.models.db import SessionLocal
from prep.models.orm import (
    Booking,
    BookingStatus,
    COIDocument,
    ComplianceDocument,
    ComplianceDocumentStatus,
    Kitchen,
    User,
    UserRole,
)
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


class StubHTML:
    """Deterministic HTML renderer used in tests to capture rendered output."""

    last_rendered: ClassVar[str | None] = None

    def __init__(self, string: str):
        type(self).last_rendered = string

    def write_pdf(self) -> bytes:
        return b"%PDF-stub%"


class StubStorageClient:
    """In-memory storage client capturing upload and presign requests."""

    def __init__(self) -> None:
        self.put_calls: list[dict[str, Any]] = []
        self.presign_calls: list[dict[str, Any]] = []

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:
        self.put_calls.append(
            {
                "Bucket": Bucket,
                "Key": Key,
                "Body": Body,
                "ContentType": ContentType,
            }
        )

    def generate_presigned_url(
        self, client_method: str, *, Params: dict[str, Any], ExpiresIn: int
    ) -> str:
        url = f"https://mock-s3.local/{Params['Key']}?ttl={ExpiresIn}"
        self.presign_calls.append(
            {
                "client_method": client_method,
                "params": Params,
                "expires_in": ExpiresIn,
                "url": url,
            }
        )
        return url


@pytest.fixture()
def packet_client() -> Generator[tuple[TestClient, Any, StubStorageClient, StubHTML], None, None]:
    module = importlib.reload(compliance_main)
    storage = StubStorageClient()
    StubHTML.last_rendered = None
    module.HTMLRenderer = StubHTML
    test_client = TestClient(module.app)
    test_client.app.dependency_overrides[module.get_storage_client] = lambda: storage
    try:
        yield test_client, module, storage, StubHTML
    finally:
        test_client.app.dependency_overrides.clear()
        test_client.close()


def _seed_booking_with_documents(session: Session) -> str:
    host = User(
        email="host@example.com",
        full_name="Regulatory Host",
        role=UserRole.HOST,
    )
    customer = User(
        email="guest@example.com",
        full_name="Booking Guest",
        role=UserRole.CUSTOMER,
    )
    kitchen = Kitchen(
        host=host,
        name="Compliance Test Kitchen",
        city="Austin",
        state="TX",
        compliance_status="compliant",
        health_permit_number="HP-12345",
        last_inspection_date=datetime.now(UTC) - timedelta(days=35),
        insurance_info={"policy_number": "PN-456"},
        zoning_type="commercial",
    )

    session.add_all([host, customer, kitchen])
    session.flush()

    start_time = datetime.now(UTC) + timedelta(days=14)
    end_time = start_time + timedelta(hours=6)

    booking = Booking(
        kitchen_id=kitchen.id,
        host_id=host.id,
        customer_id=customer.id,
        status=BookingStatus.CONFIRMED,
        start_time=start_time,
        end_time=end_time,
        total_amount=Decimal("275.00"),
        host_payout_amount=Decimal("215.00"),
    )

    session.add(booking)
    session.flush()

    documents = [
        ComplianceDocument(
            kitchen_id=kitchen.id,
            uploader_id=host.id,
            document_type="Health Permit",
            document_url="https://cdn.prep.local/health-permit.pdf",
            verification_status=ComplianceDocumentStatus.APPROVED,
            submitted_at=datetime.now(UTC) - timedelta(days=20),
            notes="City of Austin Health Department",
        ),
        ComplianceDocument(
            kitchen_id=kitchen.id,
            uploader_id=host.id,
            document_type="Fire Inspection",
            document_url="https://cdn.prep.local/fire-inspection.pdf",
            verification_status=ComplianceDocumentStatus.PENDING,
            submitted_at=datetime.now(UTC) - timedelta(days=10),
            notes="Awaiting fire marshal sign-off",
        ),
    ]

    session.add_all(documents)
    session.commit()

    return str(booking.id)


def _cleanup_booking_records(session: Session) -> None:
    session.query(ComplianceDocument).delete()
    session.query(Booking).delete()
    session.query(Kitchen).delete()
    session.query(User).delete()
    session.commit()


def test_get_regulatory_status(client: TestClient) -> None:
    response = client.get("/api/v1/regulatory/status", headers=_headers("host"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_status"] in {"on_track", "action_required"}
    assert "score" in payload
    assert "last_updated" in payload


def _mock_coi(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    class _Image:
        pass

    monkeypatch.setattr(
        coi_validator,
        "convert_from_bytes",
        lambda _: [_Image()],
    )
    monkeypatch.setattr(
        coi_validator,
        "pytesseract",
        SimpleNamespace(image_to_string=lambda __: text),
    )


def test_upload_coi_persists_metadata(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_coi(
        monkeypatch,
        (
            "Policy Number: P-123456\n"
            "Named Insured: Prep Kitchens LLC\n"
            "Expiration Date: December 31, 2099\n"
        ),
    )
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
        assert document.policy_number == "P-123456"
        assert document.insured_name == "Prep Kitchens LLC"
        assert document.expiry_date.tzinfo is not None
    finally:
        session.query(COIDocument).delete()
        session.commit()
        session.close()


def test_upload_coi_marks_expired_documents_invalid(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_coi(
        monkeypatch,
        ("Policy Number: OLD-01\nNamed Insured: Legacy Prep\nExpiration Date: January 1, 2000\n"),
    )
    response = client.post(
        "/coi",
        files={"file": ("expired.pdf", b"%PDF", "application/pdf")},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["valid"] is False
    expiry = datetime.fromisoformat(payload["expiry_date"])
    assert expiry.year == 2000
    assert expiry.tzinfo is not None
    assert expiry.tzinfo.utcoffset(expiry) == timedelta(0)


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


def test_generate_compliance_packet_creates_pdf_and_metadata(
    packet_client: tuple[TestClient, Any, StubStorageClient, StubHTML],
    db_session: Session,
) -> None:
    client, _, storage, html_renderer = packet_client
    booking_id = _seed_booking_with_documents(db_session)
    try:
        response = client.post(
            f"/packet/{booking_id}",
            headers=_headers("admin"),
        )
        assert response.status_code == 200
        payload = response.json()

        assert storage.put_calls, "Expected the packet to be uploaded to storage"
        upload = storage.put_calls[0]
        assert upload["ContentType"] == "application/pdf"
        assert upload["Body"] == b"%PDF-stub%"

        assert storage.presign_calls, "Expected a presigned URL to be generated"
        presign = storage.presign_calls[0]
        assert payload["packet_url"] == presign["url"]
        assert payload["expires_in"] == presign["expires_in"]

        metadata = payload["metadata"]
        assert metadata["booking"]["id"] == booking_id
        assert metadata["kitchen"]["insurance_policy_number"] == "PN-456"
        assert {doc["document_type"] for doc in metadata["documents"]} == {
            "Health Permit",
            "Fire Inspection",
        }

        assert html_renderer.last_rendered is not None
        assert "Health Permit" in html_renderer.last_rendered
        assert "PN-456" in html_renderer.last_rendered
    finally:
        _cleanup_booking_records(db_session)


def test_generate_compliance_packet_handles_missing_booking(
    packet_client: tuple[TestClient, Any, StubStorageClient, StubHTML],
) -> None:
    client, _, storage, _ = packet_client

    response = client.post("/packet/not-a-uuid", headers=_headers("admin"))
    assert response.status_code == 400
    assert not storage.put_calls

    response = client.post(
        "/packet/00000000-0000-0000-0000-000000000000",
        headers=_headers("admin"),
    )
    assert response.status_code == 404
    assert not storage.put_calls


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
