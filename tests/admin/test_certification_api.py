from datetime import datetime, timezone
from typing import Tuple

from fastapi import FastAPI
from fastapi.testclient import TestClient

from prep.admin import (
    CertificationVerificationAPI,
    certification_router,
    get_certification_verification_api,
)
from prep.admin.certification_api import SUNSET_HEALTH_CERT_ID
from prep.models.certification_models import CertificationDocumentStatus


def _setup_client() -> Tuple[TestClient, CertificationVerificationAPI]:
    api = CertificationVerificationAPI()
    app = FastAPI()
    app.include_router(certification_router)
    app.dependency_overrides[get_certification_verification_api] = lambda: api
    return TestClient(app), api


def test_list_pending_certifications_returns_pending_documents() -> None:
    client, _ = _setup_client()

    response = client.get("/api/v1/admin/certifications/pending")
    payload = response.json()

    assert response.status_code == 200
    assert payload["total_count"] == 2
    assert payload["has_more"] is False
    assert {item["document_type"] for item in payload["certifications"]} == {
        "health_department",
        "fire_safety",
    }


def test_get_certification_detail_includes_contextual_information() -> None:
    client, _ = _setup_client()

    response = client.get(f"/api/v1/admin/certifications/{SUNSET_HEALTH_CERT_ID}")
    payload = response.json()

    assert response.status_code == 200
    assert payload["kitchen_name"] == "Sunset Loft Kitchen"
    assert payload["host_name"] == "Ava Johnson"
    assert payload["available_actions"] == [
        "verify",
        "reject",
        "request_renewal",
    ]
    assert payload["status_history"] == []


def test_verify_certification_updates_status_and_history() -> None:
    client, _ = _setup_client()

    verify_response = client.post(
        f"/api/v1/admin/certifications/{SUNSET_HEALTH_CERT_ID}/verify",
        json={"action": "verify", "notes": "All criteria met."},
    )

    assert verify_response.status_code == 200
    assert verify_response.json()["new_status"] == CertificationDocumentStatus.VERIFIED.value

    detail_response = client.get(f"/api/v1/admin/certifications/{SUNSET_HEALTH_CERT_ID}")
    detail = detail_response.json()

    assert detail["certification"]["status"] == CertificationDocumentStatus.VERIFIED.value
    assert detail["status_history"][0]["action"] == "verify"
    assert detail["status_history"][0]["notes"] == "All criteria met."

    pending_response = client.get("/api/v1/admin/certifications/pending")
    assert pending_response.json()["total_count"] == 1


def test_request_renewal_keeps_certification_in_pending_queue() -> None:
    client, _ = _setup_client()

    renewal_response = client.post(
        f"/api/v1/admin/certifications/{SUNSET_HEALTH_CERT_ID}/verify",
        json={
            "action": "request_renewal",
            "notes": "Please upload the updated permit.",
            "expiration_date": datetime(2025, 7, 1, tzinfo=timezone.utc).isoformat(),
        },
    )

    assert renewal_response.status_code == 200
    assert (
        renewal_response.json()["new_status"]
        == CertificationDocumentStatus.RENEWAL_REQUESTED.value
    )

    pending_response = client.get("/api/v1/admin/certifications/pending")
    pending_payload = pending_response.json()

    assert pending_payload["total_count"] == 2
    renewal_statuses = {
        item["id"]: item for item in pending_payload["certifications"]
    }
    assert str(SUNSET_HEALTH_CERT_ID) in renewal_statuses

