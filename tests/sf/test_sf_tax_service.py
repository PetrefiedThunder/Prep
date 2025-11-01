from __future__ import annotations

import importlib
import sys
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def tax_client(tmp_path, monkeypatch) -> TestClient:
    db_path = tmp_path / "sf_tax.db"
    monkeypatch.setenv("SF_DATABASE_URL", f"sqlite:///{db_path}")

    for module_name in [
        "apps.tax_sf.main",
        "apps.tax_sf.services",
        "apps.sf_regulatory_service.main",
        "apps.sf_regulatory_service.services",
        "apps.sf_regulatory_service.models",
        "apps.sf_regulatory_service.database",
        "apps.sf_regulatory_service.schemas",
    ]:
        sys.modules.pop(module_name, None)
    sys.modules.pop("apps.sf_regulatory_service", None)
    sys.modules.pop("apps.tax_sf", None)

    importlib.import_module("apps.sf_regulatory_service.database")
    importlib.import_module("apps.sf_regulatory_service.models")
    importlib.import_module("apps.sf_regulatory_service.schemas")
    importlib.import_module("apps.sf_regulatory_service.services")
    importlib.import_module("apps.sf_regulatory_service.main")
    importlib.import_module("apps.tax_sf.services")
    importlib.import_module("apps.tax_sf.main")

    from apps.sf_regulatory_service.database import SessionLocal, init_db
    from apps.sf_regulatory_service.schemas import SFHostProfilePayload
    from apps.sf_regulatory_service.services import SFRegulatoryService
    from apps.tax_sf import main as tax_main

    init_db()
    with SessionLocal() as session:
        service = SFRegulatoryService(session)
        today = date.today()
        payload = SFHostProfilePayload(
            hostKitchenId="host-tax",
            businessRegistrationCertificate="BRC-999",
            businessRegistrationExpires=today + timedelta(days=120),
            healthPermitNumber="HP-999",
            healthPermitExpires=today + timedelta(days=120),
            facilityType="cooking_kitchen",
            zoningUseDistrict="PDR",
            fireSuppressionCertificate="FIRE-XYZ",
            fireLastInspection=today - timedelta(days=90),
            greaseTrapCertificate="G-XYZ",
            greaseLastService=today - timedelta(days=60),
            taxClassification="lease_sublease",
            leaseGrossReceiptsYtd=300000.0,
        )
        service.onboard_host(payload)
        session.commit()

    tax_app = tax_main.create_app()
    client = TestClient(tax_app)
    return client


def test_tax_calculate_crt_line(tax_client: TestClient) -> None:
    response = tax_client.post(
        "/sf/tax/calculate",
        json={
            "bookingId": "booking-1",
            "hostKitchenId": "host-tax",
            "city": "San Francisco",
            "bookingAmount": 1000.0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["lines"][0]["jurisdiction"] == "SF-CRT"
    assert pytest.approx(body["totalTax"], 0.01) == 35.0


def test_tax_calculate_grt_flag(tax_client: TestClient) -> None:
    # Update host classification to service provider
    from apps.sf_regulatory_service.database import SessionLocal
    from apps.sf_regulatory_service.schemas import SFHostProfilePayload
    from apps.sf_regulatory_service.services import SFRegulatoryService

    with SessionLocal() as session:
        service = SFRegulatoryService(session)
        today = date.today()
        payload = SFHostProfilePayload(
            hostKitchenId="host-tax",
            businessRegistrationCertificate="BRC-999",
            businessRegistrationExpires=today + timedelta(days=120),
            healthPermitNumber="HP-999",
            healthPermitExpires=today + timedelta(days=120),
            facilityType="commissary_non_cooking",
            zoningUseDistrict="NC-3",
            fireSuppressionCertificate=None,
            fireLastInspection=None,
            greaseTrapCertificate="G-XYZ",
            greaseLastService=today - timedelta(days=60),
            taxClassification="service_provider",
            leaseGrossReceiptsYtd=150000.0,
        )
        service.onboard_host(payload)
        session.commit()

    response = tax_client.post(
        "/sf/tax/calculate",
        json={
            "bookingId": "booking-2",
            "hostKitchenId": "host-tax",
            "city": "San Francisco",
            "bookingAmount": 750.0,
        },
    )
    body = response.json()
    assert body["lines"][0]["jurisdiction"] == "SF-GRT"
    assert body["lines"][0]["amount"] == 0


def test_tax_report_generation(tax_client: TestClient) -> None:
    tax_client.post(
        "/sf/tax/calculate",
        json={
            "bookingId": "booking-3",
            "hostKitchenId": "host-tax",
            "city": "San Francisco",
            "bookingAmount": 500.0,
        },
    )

    today = date.today()
    quarter = (today.month - 1) // 3 + 1
    response = tax_client.get("/sf/tax/report", params={"period": f"{today.year}-Q{quarter}"})
    assert response.status_code == 200
    body = response.json()
    assert "csv" in body
    assert "SF-CRT" in body["csv"] or "SF-GRT" in body["csv"]
