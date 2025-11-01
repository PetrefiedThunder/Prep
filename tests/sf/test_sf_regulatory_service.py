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
