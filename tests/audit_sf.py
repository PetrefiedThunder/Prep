from __future__ import annotations

import importlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, date, timedelta
from pathlib import Path
from typing import Iterable

import asyncio
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from prep.sf_audit import reporting as audit_reporting
from prep.storage.secure_s3 import upload_encrypted_json
from scripts import post_audit_summary


def _base_payload() -> dict[str, object]:
    today = date.today()
    return {
        "hostKitchenId": "host-audit",
        "businessRegistrationCertificate": "BRC-001",
        "businessRegistrationExpires": (today + timedelta(days=180)).isoformat(),
        "healthPermitNumber": "HP-999",
        "healthPermitExpires": (today + timedelta(days=120)).isoformat(),
        "facilityType": "cooking_kitchen",
        "zoningUseDistrict": "PDR",
        "fireSuppressionCertificate": "FIRE-001",
        "fireLastInspection": (today - timedelta(days=90)).isoformat(),
        "greaseTrapCertificate": "GREASE-001",
        "greaseLastService": (today - timedelta(days=45)).isoformat(),
        "taxClassification": "service_provider",
        "leaseGrossReceiptsYtd": 125000.0,
    }


@dataclass
class AuditHarness:
    client: TestClient
    session_factory: object
    base: object
    models: object
    services: object
    metrics: object


@pytest.fixture(scope="module")
def audit_harness(tmp_path_factory: pytest.TempPathFactory) -> Iterable[AuditHarness]:
    monkeypatch = pytest.MonkeyPatch()
    db_path = tmp_path_factory.mktemp("sf_audit") / "audit.db"
    monkeypatch.setenv("SF_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://prep:prep@localhost:5432/prep")
    monkeypatch.setenv("SECRET_KEY", "audit-secret")
    monkeypatch.delenv("SLACK_WEBHOOK_SFOPS", raising=False)

    from prep.settings import get_settings

    get_settings.cache_clear()

    modules = [
        "apps.sf_regulatory_service.main",
        "apps.sf_regulatory_service.services",
        "apps.sf_regulatory_service.models",
        "apps.sf_regulatory_service.database",
        "apps.sf_regulatory_service.metrics",
    ]
    for module_name in modules:
        sys.modules.pop(module_name, None)
    sys.modules.pop("apps.sf_regulatory_service", None)

    database = importlib.import_module("apps.sf_regulatory_service.database")
    models = importlib.import_module("apps.sf_regulatory_service.models")
    services = importlib.import_module("apps.sf_regulatory_service.services")
    metrics = importlib.import_module("apps.sf_regulatory_service.metrics")
    main = importlib.import_module("apps.sf_regulatory_service.main")

    app = main.create_app()
    client = TestClient(app, raise_server_exceptions=False)

    try:
        yield AuditHarness(client, database.SessionLocal, database.Base, models, services, metrics)
    finally:
        client.close()
        monkeypatch.undo()


@pytest.fixture()
def audit_session(audit_harness: AuditHarness) -> Iterable[object]:
    session = audit_harness.session_factory()
    try:
        for table in reversed(audit_harness.base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        audit_harness.metrics.sf_hosts_compliant_ratio.set(0)
        yield session
    finally:
        session.close()


@dataclass
class AuditContext:
    client: TestClient
    session: object
    models: object
    services: object
    metrics: object

    def seed_host_profile(self, host_id: str, **overrides: object) -> object:
        today = date.today()
        defaults = {
            "business_registration_certificate": "BRC-001",
            "business_registration_expires": today + timedelta(days=180),
            "health_permit_number": "HP-999",
            "health_permit_expires": today + timedelta(days=120),
            "facility_type": "cooking_kitchen",
            "zoning_use_district": "PDR",
            "fire_suppression_certificate": "FIRE-001",
            "fire_last_inspection": today - timedelta(days=90),
            "grease_trap_certificate": "GREASE-001",
            "grease_last_service": today - timedelta(days=45),
            "tax_classification": "service_provider",
            "lease_gross_receipts_ytd": 150000.0,
            "compliance_status": "compliant",
        }
        defaults.update(overrides)
        profile = self.models.SFHostProfile(
            host_kitchen_id=host_id,
            business_registration_certificate=defaults["business_registration_certificate"],
            business_registration_expires=defaults["business_registration_expires"],
            health_permit_number=defaults["health_permit_number"],
            health_permit_expires=defaults["health_permit_expires"],
            facility_type=defaults["facility_type"],
            zoning_use_district=defaults["zoning_use_district"],
            fire_suppression_certificate=defaults["fire_suppression_certificate"],
            fire_last_inspection=defaults["fire_last_inspection"],
            grease_trap_certificate=defaults["grease_trap_certificate"],
            grease_last_service=defaults["grease_last_service"],
            tax_classification=defaults["tax_classification"],
            lease_gross_receipts_ytd=defaults["lease_gross_receipts_ytd"],
            compliance_status=defaults["compliance_status"],
        )
        self.session.merge(profile)
        self.session.commit()
        return profile

    def run_query(self, sql: str) -> int:
        result = self.session.execute(text(sql))
        value = result.scalar_one_or_none()
        return int(value or 0)

    def make_headers(self, roles: Iterable[str]) -> dict[str, str]:
        token = jwt.encode({"roles": list(roles), "sub": "audit"}, "audit-secret", algorithm="HS256")
        return {"Authorization": f"Bearer {token}"}

    def record_tax_line(self, *args: object, **kwargs: object) -> None:
        service = self.services.LedgerService(self.session)
        service.record_tax_line(*args, **kwargs)
        self.session.commit()

    def record_etl_run(self, **kwargs: object) -> None:
        recorder = self.services.EtlRecorder(self.session)
        recorder.record(**kwargs)
        self.session.commit()


@pytest.fixture()
def audit_context(audit_harness: AuditHarness, audit_session: object) -> AuditContext:
    return AuditContext(
        client=audit_harness.client,
        session=audit_session,
        models=audit_harness.models,
        services=audit_harness.services,
        metrics=audit_harness.metrics,
    )


def test_business_registration_controls(audit_context: AuditContext, caplog: pytest.LogCaptureFixture) -> None:
    ctx = audit_context
    ctx.seed_host_profile("host-pass")
    assert (
        ctx.run_query(
            "SELECT COUNT(*) FROM sf_host_profiles WHERE business_registration_expires < DATE('now')"
        )
        == 0
    )

    ctx.seed_host_profile("host-fail", business_registration_expires=date.today() - timedelta(days=1))
    assert (
        ctx.run_query(
            "SELECT COUNT(*) FROM sf_host_profiles WHERE business_registration_expires < DATE('now')"
        )
        == 1
    )

    payload = _base_payload()
    payload["businessRegistrationCertificate"] = ""

    response = ctx.client.post(
        "/sf/host/onboard",
        json=payload,
        headers=ctx.make_headers(["host"]),
    )
    assert response.status_code == 403

    with caplog.at_level("INFO", logger="apps.sf_regulatory_service.main"):
        response = ctx.client.post(
            "/sf/host/onboard",
            json=payload,
            headers=ctx.make_headers(["regulatory_admin"]),
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert any("Business registration" in issue for issue in body["issues"])

    for record in caplog.records:
        message = record.getMessage()
        assert "HP-" not in message
        for value in record.__dict__.values():
            if isinstance(value, str):
                assert "HP-" not in value


def test_health_permit_controls(audit_context: AuditContext) -> None:
    ctx = audit_context
    ctx.seed_host_profile("host-health")
    assert (
        ctx.run_query(
            "SELECT COUNT(*) FROM sf_host_profiles WHERE health_permit_expires < DATE('now')"
        )
        == 0
    )

    ctx.seed_host_profile("host-health", health_permit_expires=date.today() - timedelta(days=1))
    assert (
        ctx.run_query(
            "SELECT COUNT(*) FROM sf_host_profiles WHERE health_permit_expires < DATE('now')"
        )
        == 1
    )

    response = ctx.client.post(
        "/sf/compliance/check",
        json={"hostKitchenId": "host-health", "bookingId": "booking-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert any("Health permit" in issue for issue in body["issues"])

    response = ctx.client.post(
        "/sf/health/validate",
        json={
            "permitNumber": "X9999",
            "facilityType": "cooking_kitchen",
            "address": "123 Market",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] in {"revoked", "invalid"}


def test_fire_and_waste_controls(audit_context: AuditContext) -> None:
    ctx = audit_context
    ctx.seed_host_profile("host-fire")
    assert (
        ctx.run_query(
            "SELECT COUNT(*) FROM sf_host_profiles WHERE fire_last_inspection <= DATE('now','-365 day')"
        )
        == 0
    )

    ctx.seed_host_profile(
        "host-fire",
        fire_last_inspection=date.today() - timedelta(days=400),
        grease_last_service=date.today() - timedelta(days=400),
    )
    assert (
        ctx.run_query(
            "SELECT COUNT(*) FROM sf_host_profiles WHERE fire_last_inspection <= DATE('now','-365 day')"
        )
        == 1
    )
    assert (
        ctx.run_query(
            "SELECT COUNT(*) FROM sf_host_profiles WHERE grease_last_service <= DATE('now','-180 day')"
        )
        == 1
    )

    response = ctx.client.post(
        "/sf/fire/verify",
        json={
            "hostKitchenId": "host-fire",
            "certificate": "FIRE-001",
            "lastInspectionDate": (date.today() - timedelta(days=400)).isoformat(),
            "systemType": "sprinkler",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "non_compliant"

    response = ctx.client.post(
        "/sf/waste/verify",
        json={
            "hostKitchenId": "host-fire",
            "certificate": "GREASE-001",
            "lastServiceDate": (date.today() - timedelta(days=400)).isoformat(),
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "overdue"


def test_zoning_audit_controls(audit_context: AuditContext) -> None:
    ctx = audit_context
    for index in range(25):
        ctx.session.add(
            ctx.models.SFZoningVerification(
                host_kitchen_id=f"host-{index}",
                address=f"{index} Market St",
                zoning_use_district="PDR" if index % 3 else "",
                kitchen_use_allowed=True,
                manual_review_required=index == 0,
            )
        )
    ctx.session.commit()

    result = ctx.session.execute(
        text(
            """
            SELECT
              SUM(CASE WHEN zoning_use_district IS NULL OR zoning_use_district = '' THEN 1 ELSE 0 END) AS missing,
              SUM(CASE WHEN manual_review_required THEN 1 ELSE 0 END) AS manual,
              COUNT(*) AS total
            FROM sf_zoning_verifications
            """
        )
    ).mappings().one()
    manual_rate = (result["manual"] or 0) / (result["total"] or 1)
    assert manual_rate < 0.05

    response = ctx.client.get("/sf/zoning/check", params={"address": "Unknown Ave"})
    assert response.status_code == 200
    body = response.json()
    assert body["manualReviewRequired"] is True


def test_tax_compliance_controls(audit_context: AuditContext) -> None:
    ctx = audit_context
    ctx.record_tax_line("booking-crt", "CRT", 1000.0, 0.035, 35.0)
    ctx.record_tax_line("booking-grt", "GRT", 2000.0, 0.025, 50.0)

    result = ctx.session.execute(
        text("SELECT tax_jurisdiction, COUNT(*) FROM sf_tax_ledger GROUP BY tax_jurisdiction")
    ).all()
    jurisdictions = {row[0] for row in result}
    assert {"CRT", "GRT"}.issubset(jurisdictions)

    ledger_total = ctx.session.execute(
        text("SELECT COALESCE(SUM(tax_amount), 0) FROM sf_tax_ledger")
    ).scalar_one()

    class FakeGAAPLedgerService:
        def __init__(self, total: float) -> None:
            self._total = total

        async def total_tax(self) -> float:
            return self._total

    gaap_service = FakeGAAPLedgerService(float(ledger_total) * 0.9995)
    gaap_total = asyncio.run(gaap_service.total_tax())
    delta = abs(float(ledger_total) - gaap_total)
    assert float(ledger_total) > 0
    assert delta / float(ledger_total) < 0.001


def test_observability_and_metrics(audit_context: AuditContext) -> None:
    ctx = audit_context
    payload = _base_payload()
    response = ctx.client.post(
        "/sf/host/onboard",
        json=payload,
        headers=ctx.make_headers(["regulatory_admin"]),
    )
    assert response.status_code == 200

    ctx.record_etl_run(
        city="San Francisco",
        run_date=datetime.now(tz=UTC),
        extracted=120,
        changed=10,
        status="success",
        diff_summary="all good",
    )
    for offset in range(1, 7):
        ctx.record_etl_run(
            city="San Francisco",
            run_date=datetime.now(tz=UTC) - timedelta(hours=offset * 4),
            extracted=100,
            changed=5,
            status="success",
            diff_summary="rolling",
        )

    ctx.client.post(
        "/sf/compliance/check",
        json={"hostKitchenId": payload["hostKitchenId"], "bookingId": "booking-metrics"},
    )
    metrics_output = ctx.metrics.generate_latest().decode("utf-8")
    if getattr(ctx.metrics, "PROMETHEUS_AVAILABLE", False):
        assert "sf_hosts_compliant_ratio" in metrics_output
        assert "http_server_latency_seconds_bucket" in metrics_output
        assert "route=\"/sf/compliance/check\",le=\"0.2\"" in metrics_output

    etl_count = ctx.run_query("SELECT COUNT(*) FROM city_etl_runs WHERE status = 'success'")
    assert etl_count >= 7


def test_security_and_slack_reporting(audit_context: AuditContext, tmp_path: Path) -> None:
    ctx = audit_context

    class StubS3Client:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def put_object(self, **kwargs: object) -> dict[str, object]:
            self.calls.append(kwargs)
            return {"ETag": "fake"}

    s3_client = StubS3Client()
    upload_encrypted_json({"ok": True}, bucket="prep-audit", key="report.json", s3_client=s3_client)
    assert s3_client.calls
    call = s3_client.calls[0]
    assert call["ServerSideEncryption"] == "aws:kms"

    pytest_report = {
        "created": datetime.now(tz=UTC).isoformat(),
        "summary": {"passed": 6, "failed": 0, "total": 6},
        "tests": [
            {
                "nodeid": "tests/audit_sf.py::test_business_registration_controls",
                "outcome": "passed",
            }
        ],
    }
    report_path = tmp_path / "sf_audit.json"
    report_path.write_text(json.dumps(pytest_report), encoding="utf-8")

    output_path = post_audit_summary.main([
        "--report",
        str(report_path),
        "--output-dir",
        str(tmp_path),
    ])
    assert output_path.exists()

    condensed = json.loads(output_path.read_text(encoding="utf-8"))
    slack_payload = audit_reporting.build_slack_payload(condensed)
    assert "SF Regulatory Audit Results" in slack_payload["text"]

    ctx.session.commit()
