from __future__ import annotations

import importlib
import sys
from datetime import date, timedelta
from typing import Dict

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def regulatory_client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "sf_reg.db"
    monkeypatch.setenv("SF_DATABASE_URL", f"sqlite:///{db_path}")

    for module_name in [
        "apps.sf_regulatory_service.main",
        "apps.sf_regulatory_service.services",
        "apps.sf_regulatory_service.models",
        "apps.sf_regulatory_service.database",
    ]:
        sys.modules.pop(module_name, None)
    sys.modules.pop("apps.sf_regulatory_service", None)

    importlib.import_module("apps.sf_regulatory_service.database")
    importlib.import_module("apps.sf_regulatory_service.models")
    importlib.import_module("apps.sf_regulatory_service.services")
    importlib.import_module("apps.sf_regulatory_service.main")

    from apps.sf_regulatory_service import main

    app = main.create_app()
    client = TestClient(app)
    return client


def _base_payload() -> Dict[str, object]:
    today = date.today()
    return {
        "hostKitchenId": "host-1",
        "businessRegistrationCertificate": "BRC-123",
        "businessRegistrationExpires": (today + timedelta(days=200)).isoformat(),
        "healthPermitNumber": "HP-123",
        "healthPermitExpires": (today + timedelta(days=180)).isoformat(),
        "facilityType": "cooking_kitchen",
        "zoningUseDistrict": "PDR",
        "fireSuppressionCertificate": "FIRE-001",
        "fireLastInspection": (today - timedelta(days=100)).isoformat(),
        "greaseTrapCertificate": "GREASE-001",
        "greaseLastService": (today - timedelta(days=50)).isoformat(),
        "taxClassification": "lease_sublease",
        "leaseGrossReceiptsYtd": 250000.0,
    }


def _counter_value(status: str) -> float | None:
    from apps.sf_regulatory_service import metrics

    counter = metrics.sf_compliance_check_total.labels(status=status)
    value = getattr(counter, "_value", None)
    getter = getattr(value, "get", None) if value is not None else None
    return getter() if callable(getter) else None


def test_host_onboard_compliant(regulatory_client: TestClient) -> None:
    payload = _base_payload()
    response = regulatory_client.post("/sf/host/onboard", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "compliant"
    assert body["issues"] == []


def test_host_onboard_missing_business_registration(regulatory_client: TestClient) -> None:
    payload = _base_payload()
    payload["businessRegistrationCertificate"] = ""
    response = regulatory_client.post("/sf/host/onboard", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert any("Business registration" in issue for issue in body["issues"])


def test_host_onboard_blocks_missing_grease_certificate(regulatory_client: TestClient) -> None:
    payload = _base_payload()
    payload["greaseTrapCertificate"] = ""
    response = regulatory_client.post("/sf/host/onboard", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert "Grease trap service documentation is required" in body["issues"]


def test_host_onboard_blocks_missing_grease_service_date(regulatory_client: TestClient) -> None:
    payload = _base_payload()
    payload.pop("greaseLastService")
    response = regulatory_client.post("/sf/host/onboard", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert "Grease trap service date is required" in body["issues"]


def test_host_onboard_flags_grease_due_soon(regulatory_client: TestClient) -> None:
    payload = _base_payload()
    payload["greaseLastService"] = (date.today() - timedelta(days=155)).isoformat()
    response = regulatory_client.post("/sf/host/onboard", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "flagged"
    assert "Grease interceptor service due soon" in body["issues"]


def test_host_onboard_blocks_grease_overdue(regulatory_client: TestClient) -> None:
    payload = _base_payload()
    payload["greaseLastService"] = (date.today() - timedelta(days=200)).isoformat()
    response = regulatory_client.post("/sf/host/onboard", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert "Grease interceptor service interval exceeded" in body["issues"]


def test_compliance_check_blocks_for_stale_fire(regulatory_client: TestClient) -> None:
    payload = _base_payload()
    payload["fireLastInspection"] = (date.today() - timedelta(days=500)).isoformat()
    regulatory_client.post("/sf/host/onboard", json=payload)

    response = regulatory_client.post(
        "/sf/compliance/check",
        json={"hostKitchenId": payload["hostKitchenId"], "bookingId": "booking-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert any("Fire" in issue for issue in body["issues"])


def test_zoning_check_manual_review(regulatory_client: TestClient) -> None:
    response = regulatory_client.get(
        "/sf/zoning/check",
        params={"address": "Unknown Ave", "district": "RES"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["kitchenUseAllowed"] is False
    assert body["manualReviewRequired"] is False


def test_booking_blocked_for_nonexistent_host(regulatory_client: TestClient) -> None:
    response = regulatory_client.post(
        "/sf/compliance/check",
        json={"hostKitchenId": "missing", "bookingId": "booking-123"},
    )
    assert response.status_code == 404


def test_sf_booking_kernel_records_passed_decision(regulatory_client: TestClient) -> None:
    payload = _base_payload()
    regulatory_client.post("/sf/host/onboard", json=payload)

    from apps.sf_regulatory_service.database import SessionLocal
    from apps.sf_regulatory_service.models import SFBookingCompliance

    passed_before = _counter_value("passed")

    booking_id = "booking-pass"
    response = regulatory_client.post(
        "/sf/compliance/check",
        json={"hostKitchenId": payload["hostKitchenId"], "bookingId": booking_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "passed"
    assert body["issues"] == []

    with SessionLocal() as session:
        record = session.get(SFBookingCompliance, booking_id)
        assert record is not None
        assert record.prebooking_status == "passed"
        assert record.issues == []

    passed_after = _counter_value("passed")
    if passed_before is not None and passed_after is not None:
        assert passed_after == passed_before + 1


def test_sf_booking_kernel_blocks_missing_fire_permit(regulatory_client: TestClient) -> None:
    payload = _base_payload()
    payload["fireSuppressionCertificate"] = ""
    payload["fireLastInspection"] = (date.today() - timedelta(days=30)).isoformat()
    regulatory_client.post("/sf/host/onboard", json=payload)

    from apps.sf_regulatory_service.database import SessionLocal
    from apps.sf_regulatory_service.models import SFBookingCompliance

    blocked_before = _counter_value("blocked")

    booking_id = "booking-blocked"
    response = regulatory_client.post(
        "/sf/compliance/check",
        json={"hostKitchenId": payload["hostKitchenId"], "bookingId": booking_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert any("Missing or expired fire permit" in issue for issue in body["issues"])

    with SessionLocal() as session:
        record = session.get(SFBookingCompliance, booking_id)
        assert record is not None
        assert record.prebooking_status == "blocked"
        assert any("Missing or expired fire permit" in issue for issue in record.issues)

    blocked_after = _counter_value("blocked")
    if blocked_before is not None and blocked_after is not None:
        assert blocked_after == blocked_before + 1
