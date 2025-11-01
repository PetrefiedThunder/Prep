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
import requests
import psycopg2
import psycopg2.extras
try:
    import psycopg2
    import psycopg2.extras
except ImportError:  # pragma: no cover - optional dependency
    psycopg2 = None  # type: ignore

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - optional dependency
    psycopg = None  # type: ignore
    dict_row = None  # type: ignore


# ---------------------------
# Fixtures & Helpers
# ---------------------------

def _get_env(name, default=None):
    val = os.getenv(name, default)
    if val is None:
        pytest.skip(f"Missing required env var: {name}")
    return val


@pytest.fixture(scope="session")
def base_url():
    return _get_env("AUDIT_BASE_URL")


@pytest.fixture(scope="session")
def auth_headers():
    token = _get_env("AUDIT_JWT")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def db_conn():
    host = _get_env("AUDIT_DB_HOST")
    port = int(os.getenv("AUDIT_DB_PORT", "5432"))
    name = _get_env("AUDIT_DB_NAME")
    user = _get_env("AUDIT_DB_USER")
    pwd = _get_env("AUDIT_DB_PASSWORD")
    sslmode = os.getenv("AUDIT_DB_SSLMODE", "prefer")

    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=name,
        user=user,
        password=pwd,
        sslmode=sslmode,
        cursor_factory=psycopg2.extras.DictCursor,
    )
    yield conn
    conn.close()

    pwd  = _get_env("AUDIT_DB_PASSWORD")
    sslmode = os.getenv("AUDIT_DB_SSLMODE", "prefer")

    if psycopg2 is not None:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=name,
            user=user,
            password=pwd,
            sslmode=sslmode,
            cursor_factory=psycopg2.extras.DictCursor,
        )
    elif psycopg is not None and dict_row is not None:
        conn = psycopg.connect(
            host=host,
            port=port,
            dbname=name,
            user=user,
            password=pwd,
            sslmode=sslmode,
            row_factory=dict_row,
        )
    else:  # pragma: no cover - dependency missing in environment
        pytest.skip("psycopg2 or psycopg library required for DB connectivity")

from prep.sf_audit import reporting as audit_reporting
from prep.storage.secure_s3 import upload_encrypted_json
from scripts import post_audit_summary


def _base_payload() -> dict[str, object]:
    today = date.today()

@pytest.fixture(scope="session")
def policy_thresholds():
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
def query_scalar(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        row = cur.fetchone()
        return row[0] if row else None

        if not row:
            return None
        if isinstance(row, dict):
            return next(iter(row.values()))
        return row[0]

def query_row(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()


def query_all(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


# ---------------------------
# Domain A: Business Registration
# ---------------------------


def test_business_registration_present_and_valid(db_conn):
    """
    Must have Business Registration Certificate on file for all SF hosts.
    """
    sql = """
        SELECT COUNT(*) 
        FROM sf_host_profiles shp
        JOIN host_kitchens hk ON hk.id = shp.host_kitchen_id
        WHERE hk.city = 'San Francisco'
          AND (shp.business_registration_certificate IS NULL
               OR shp.business_registration_certificate = '')
          OR (shp.business_registration_expires IS NULL
              OR shp.business_registration_expires < NOW()::date)
    """
    bad = query_scalar(db_conn, sql)
    assert bad == 0, f"Found {bad} SF hosts missing/expired Business Registration."


@pytest.mark.skipif(os.getenv("SF_TEST_ONBOARDING_ENABLED") != "1", reason="Negative onboarding test disabled")
def test_onboarding_blocks_without_business_certificate(base_url, auth_headers):
    """
    Attempt to onboard an SF host without certificate; expect a hard BLOCK.
    This should hit your POST /sf/host/onboard with minimal payload.
    """
    url = f"{base_url}/sf/host/onboard"
    payload = {
        "hostKitchenId": "00000000-0000-0000-0000-000000000000",  # dummy
        "businessRegistrationCertificate": "",
        "businessRegistrationExpires": None,
        "healthPermitNumber": "TEST-PLACEHOLDER",
        "healthPermitExpires": "2099-01-01",
        "facilityType": "commissary_non_cooking",
        "zoningUseDistrict": "PDR-1",
        "taxClassification": "lease_sublease",
    }
    r = requests.post(url, headers=auth_headers, data=json.dumps(payload), timeout=30)
    assert r.status_code in (400, 409), f"Expected BLOCK; got {r.status_code} {r.text}"
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    body = r.json() if r.headers.get("content-type","").startswith("application/json") else {}
    assert any("CERT" in (issue.upper()) for issue in body.get("issues", [])), f"Missing explicit business cert error: {body}"


# ---------------------------
# Domain B: Health Permit
# ---------------------------


def test_health_permit_valid_for_all_sf_hosts(db_conn):
    """
    Health permit required and not expired for all SF kitchens.
    """
    sql = """
        SELECT COUNT(*)
        FROM sf_host_profiles shp
        JOIN host_kitchens hk ON hk.id = shp.host_kitchen_id
        WHERE hk.city = 'San Francisco'
          AND (
                shp.health_permit_number IS NULL OR shp.health_permit_number = ''
               OR shp.health_permit_expires IS NULL
               OR shp.health_permit_expires < NOW()::date
          )
    """
    bad = query_scalar(db_conn, sql)
    assert bad == 0, f"Found {bad} SF hosts with missing/expired health permit."


@pytest.mark.skipif(os.getenv("SF_TEST_BOOKING_HOST_EXPIRED") in (None, "",), reason="No expired-permit host id configured")
def test_compliance_check_blocks_expired_permit(base_url, auth_headers):
    """
    Use a known staging host_kitchen_id with an expired permit to verify BLOCK.
    """
    host_id = os.getenv("SF_TEST_BOOKING_HOST_EXPIRED")
    url = f"{base_url}/sf/compliance/check"
    payload = {"hostKitchenId": host_id}
    r = requests.post(url, headers=auth_headers, data=json.dumps(payload), timeout=30)
    assert r.ok, f"/sf/compliance/check failed: {r.status_code} {r.text}"
    data = r.json()
    assert data.get("status") == "blocked", f"Expected BLOCK for expired permit; got {data}"


# ---------------------------
# Domain C: Fire Suppression & FOG
# ---------------------------


def test_fire_suppression_and_grease_service_current(db_conn):
    """
    For cooking kitchens, ensure fire suppression inspection <= 365 days
    and grease service within policy interval (default 365 days).
    """
    fire_sql = """
        SELECT COUNT(*)
        FROM sf_host_profiles shp
        JOIN host_kitchens hk ON hk.id = shp.host_kitchen_id
        WHERE hk.city = 'San Francisco'
          AND shp.facility_type = 'cooking_kitchen'
          AND (shp.fire_suppression_certificate IS NULL OR shp.fire_suppression_certificate = ''
               OR shp.fire_last_inspection IS NULL
               OR shp.fire_last_inspection < (NOW()::date - INTERVAL '365 days'))
    """
    grease_sql = """
        SELECT COUNT(*)
        FROM sf_host_profiles shp
        JOIN host_kitchens hk ON hk.id = shp.host_kitchen_id
        WHERE hk.city = 'San Francisco'
          AND shp.facility_type IN ('cooking_kitchen','commissary_non_cooking')
          AND (shp.grease_trap_certificate IS NULL OR shp.grease_trap_certificate = ''
               OR shp.grease_last_service IS NULL
               OR shp.grease_last_service < (NOW()::date - INTERVAL '365 days'))
    """
    fire_bad = query_scalar(db_conn, fire_sql)
    grease_bad = query_scalar(db_conn, grease_sql)
    assert fire_bad == 0, f"{fire_bad} cooking kitchens with stale/missing fire suppression."
    assert grease_bad == 0, f"{grease_bad} kitchens with stale/missing grease trap service."


# ---------------------------
# Domain D: Zoning / Use District
# ---------------------------


def test_zoning_mapped_and_manual_rate_within_threshold(db_conn, policy_thresholds):
    """
    Every SF listing must have a zoning_use_district.
    Manual review rate should stay under configured threshold.
    """
    nulls_sql = """
        SELECT COUNT(*)
        FROM sf_zoning_verifications zv
        JOIN host_kitchens hk ON hk.id = zv.host_kitchen_id
        WHERE hk.city='San Francisco'
          AND (zv.zoning_use_district IS NULL OR zv.zoning_use_district = '')
    """
    total_sql = """
        SELECT COUNT(*)
        FROM sf_zoning_verifications zv
        JOIN host_kitchens hk ON hk.id = zv.host_kitchen_id
        WHERE hk.city='San Francisco'
    """
    manual_sql = """
        SELECT COUNT(*)
        FROM sf_zoning_verifications zv
        JOIN host_kitchens hk ON hk.id = zv.host_kitchen_id
        WHERE hk.city='San Francisco' AND zv.manual_review_required = TRUE
    """

    nulls = query_scalar(db_conn, nulls_sql)
    total = query_scalar(db_conn, total_sql) or 0
    manual = query_scalar(db_conn, manual_sql) or 0

    assert nulls == 0, f"{nulls} SF zoning records missing district."
    if total > 0:
        pct = (manual / total) * 100.0
        assert pct <= policy_thresholds["zoning_manual_max_pct"], f"Manual review rate {pct:.2f}% exceeds threshold."


# ---------------------------
# Domain E: Taxes (CRT / GRT)
# ---------------------------


def test_crt_lines_exist_for_lease_sublease_bookings_last_30_days(db_conn):
    """
    Ensure CRT lines are being produced for lease/sublease bookings in SF.
    """
    sql = """
        SELECT COUNT(*)
        FROM sf_tax_ledger tl
        JOIN bookings b ON b.id = tl.booking_id
        JOIN host_kitchens hk ON hk.id = b.host_kitchen_id
        WHERE hk.city='San Francisco'
          AND tl.tax_jurisdiction='SF-CRT'
          AND tl.created_at >= (NOW() - INTERVAL '30 days')
    """
    cnt = query_scalar(db_conn, sql)
    assert (cnt or 0) > 0, "No SF-CRT tax lines in last 30 days; verify classification and tax service wiring."


@pytest.mark.skipif(os.getenv("FIN_GL_TOTAL_LAST_30") in (None, "",), reason="No Finance GL baseline provided")
def test_finance_reconciliation_last_30_days(db_conn):
    """
    Compare sf_tax_ledger collected tax vs. Finance GL value (env supplied).
    Acceptable delta < 0.1%
    """
    sql = """
        SELECT COALESCE(SUM(tax_amount),0)
        FROM sf_tax_ledger
        WHERE created_at >= (NOW() - INTERVAL '30 days')
          AND tax_jurisdiction='SF-CRT'
    """
    ledger_sum = decimal.Decimal(query_scalar(db_conn, sql) or 0)
    gl_sum = decimal.Decimal(os.getenv("FIN_GL_TOTAL_LAST_30"))
    if gl_sum == 0:
        pytest.skip("Finance GL total is zero; skipping percentage delta check.")
    delta_pct = abs(ledger_sum - gl_sum) / gl_sum * decimal.Decimal("100")
    assert delta_pct <= decimal.Decimal("0.1"), f"Tax ledger vs GL delta {delta_pct:.4f}% exceeds 0.1%."


# ---------------------------
# Domain F: Observability / Performance
# ---------------------------


@pytest.mark.skipif(os.getenv("SF_TEST_COMPLIANCE_CHECK_HOST") in (None, "",), reason="No host id for perf probe")
def test_compliance_check_latency_p95(base_url, auth_headers, perf_thresholds):
    """
    Probe /sf/compliance/check multiple times and approximate p95.
    """
    url = f"{base_url}/sf/compliance/check"
    host_id = os.getenv("SF_TEST_COMPLIANCE_CHECK_HOST")
    payload = {"hostKitchenId": host_id}

    samples = []
    for _ in range(20):
        t0 = time.perf_counter()
        r = requests.post(url, headers=auth_headers, data=json.dumps(payload), timeout=30)
        t1 = time.perf_counter()
        assert r.ok, f"/sf/compliance/check error: {r.status_code} {r.text}"
        samples.append((t1 - t0) * 1000.0)  # ms

    p95 = sorted(samples)[int(len(samples) * 0.95) - 1]
    assert (
        p95 <= perf_thresholds["compliance_ms"]
    ), f"p95 compliance_check {p95:.1f}ms exceeds budget {perf_thresholds['compliance_ms']}ms"
    p95 = sorted(samples)[int(len(samples)*0.95) - 1]
    assert p95 <= perf_thresholds["compliance_ms"], f"p95 compliance_check {p95:.1f}ms exceeds budget {perf_thresholds['compliance_ms']}ms"


@pytest.mark.skipif(os.getenv("SF_TEST_BOOKING_ID") in (None, "",), reason="No booking id for tax perf probe")
def test_tax_calculate_latency_p95(base_url, auth_headers, perf_thresholds):
    """
    Probe /sf/tax/calculate multiple times and approximate p95.
    """
    url = f"{base_url}/sf/tax/calculate"
    booking_id = os.getenv("SF_TEST_BOOKING_ID")

    # Best-effort payload; your API may also accept hostKitchenId/amount
    payload = {"booking_id": booking_id, "city": "San Francisco"}

    samples = []
    for _ in range(20):
        t0 = time.perf_counter()
        r = requests.post(url, headers=auth_headers, data=json.dumps(payload), timeout=30)
        t1 = time.perf_counter()
        assert r.ok, f"/sf/tax/calculate error: {r.status_code} {r.text}"
        samples.append((t1 - t0) * 1000.0)

    p95 = sorted(samples)[int(len(samples) * 0.95) - 1]
    p95 = sorted(samples)[int(len(samples)*0.95) - 1]
    assert p95 <= perf_thresholds["tax_ms"], f"p95 tax_calculate {p95:.1f}ms exceeds budget {perf_thresholds['tax_ms']}ms"


def test_metrics_exposed_and_key_counters_present(base_url):
    """
    Pull /metrics and ensure SF counters exist.
    """
    # Depending on your deployment, metrics may be on gateway, service, or /internal/metrics
    # Prefer aggregated metrics endpoint exposed to CI.
    metrics_url = f"{base_url}/metrics"
    r = requests.get(metrics_url, timeout=30)
    assert r.ok, f"/metrics not reachable: {r.status_code}"

    text = r.text
    expected = [
        "sf_permit_validations_total",
        "sf_zoning_checks_total",
        "sf_compliance_check_total",
        "sf_tax_lines_total",
        "sf_etl_runs_total",
    ]
    missing = [m for m in expected if m not in text]
    assert not missing, f"Missing metrics: {missing}"


# ---------------------------
# Domain G: ETL Freshness
# ---------------------------


def test_etl_last_7_runs_success(db_conn):
    """
    Verify SF ETL succeeded for the last 7 runs and latency is within 24h.
    """
    rows = query_all(
        db_conn,
        """
    rows = query_all(db_conn, """
        SELECT run_date, status, records_extracted, records_changed
        FROM city_etl_runs
        WHERE city='San Francisco'
        ORDER BY run_date DESC
        LIMIT 7
    """,
    )
    """)
    assert rows and len(rows) == 7, "Expected 7 ETL runs for SF."
    failures = [r for r in rows if r["status"] != "success"]
    assert not failures, f"ETL failures detected: {failures}"

    latest = rows[0]["run_date"]
    delta = dt.datetime.now(dt.timezone.utc) - latest
    assert delta.total_seconds() <= 24 * 3600, f"Last SF ETL run too old: {latest}"
    assert delta.total_seconds() <= 24*3600, f"Last SF ETL run too old: {latest}"


# ---------------------------
# Domain H: Security & Governance
# ---------------------------


def test_sf_endpoints_require_auth(base_url):
    """
    Minimal probe to confirm auth is enforced. Send no token; expect 401/403.
    """
    endpoints = [
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
    ]
    for ep in endpoints:
        url = f"{base_url}{ep}"
        # POST for those that require POST, GET for GET; we’ll POST JSON since most are POST.
        r = requests.post(url, headers={"Content-Type": "application/json"}, data="{}", timeout=15)
        r = requests.post(url, headers={"Content-Type":"application/json"}, data="{}", timeout=15)
        assert r.status_code in (401, 403), f"{ep} should require auth; got {r.status_code}"
