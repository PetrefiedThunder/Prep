# tests/audit_sf.py
"""
SF Compliance Audit Suite
-------------------------
Purpose: Nightly/CI audit for San Francisco launch readiness.

Requires:
- pytest
- pytest-json-report (run with: pytest --json-report --json-report-file reports/sf_audit.json)
- requests
- psycopg2-binary (or use async adapter if your stack is async)
- A read-only DB user (recommended) configured via env

Environment Variables:
  # Core connectivity
  AUDIT_BASE_URL                 -> e.g. https://staging.api.prep.example.com
  AUDIT_JWT                      -> service-to-service JWT (or API token) for /sf/* endpoints
  AUDIT_DB_HOST
  AUDIT_DB_PORT                  -> default 5432
  AUDIT_DB_NAME
  AUDIT_DB_USER
  AUDIT_DB_PASSWORD
  AUDIT_DB_SSLMODE               -> 'require' in CI preferred (default: prefer)

  # Optional fixtures to turn on mutation/black-box tests
  SF_TEST_ONBOARDING_ENABLED     -> "1" to attempt negative onboarding path (missing cert)
  SF_TEST_BOOKING_HOST_EXPIRED   -> host_kitchen_id with expired permit (staging data)
  SF_TEST_COMPLIANCE_CHECK_HOST  -> host_kitchen_id with valid docs to measure perf
  SF_TEST_BOOKING_ID             -> booking_id for tax calc perf probe (must belong to SF)
  FIN_GL_TOTAL_LAST_30           -> decimal string, Finance GL total tax for last 30 days (recon)

  # Performance thresholds (defaults)
  SF_P95_MS_COMPLIANCE_CHECK     -> default 200
  SF_P95_MS_TAX_CALCULATE        -> default 200

  # Policy thresholds (defaults)
  SF_ZONING_MANUAL_REVIEW_MAX_PCT -> default 5.0

Notes:
- Tests that require specific host/booking IDs will SKIP when env is not set.
- SQL assumes table names from the directive:
    sf_host_profiles, sf_zoning_verifications, sf_booking_compliance,
    sf_tax_ledger, sf_tax_reports, city_etl_runs
- Adjust table/column names if your migrations differ.
"""

import os
import time
import json
import decimal
import datetime as dt

import pytest
import requests
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

    try:
        yield conn
    finally:
        conn.close()

@pytest.fixture(scope="session")
def perf_thresholds():
    return {
        "compliance_ms": int(os.getenv("SF_P95_MS_COMPLIANCE_CHECK", "200")),
        "tax_ms": int(os.getenv("SF_P95_MS_TAX_CALCULATE", "200")),
    }

@pytest.fixture(scope="session")
def policy_thresholds():
    return {
        "zoning_manual_max_pct": float(os.getenv("SF_ZONING_MANUAL_REVIEW_MAX_PCT", "5.0")),
    }

def query_scalar(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        row = cur.fetchone()
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
    rows = query_all(db_conn, """
        SELECT run_date, status, records_extracted, records_changed
        FROM city_etl_runs
        WHERE city='San Francisco'
        ORDER BY run_date DESC
        LIMIT 7
    """)
    assert rows and len(rows) == 7, "Expected 7 ETL runs for SF."
    failures = [r for r in rows if r["status"] != "success"]
    assert not failures, f"ETL failures detected: {failures}"

    latest = rows[0]["run_date"]
    delta = dt.datetime.now(dt.timezone.utc) - latest
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
        "/sf/compliance/check",
        "/sf/tax/calculate",
        "/sf/health/validate",
        "/sf/fire/verify",
        "/sf/waste/verify",
    ]
    for ep in endpoints:
        url = f"{base_url}{ep}"
        # POST for those that require POST, GET for GET; we’ll POST JSON since most are POST.
        r = requests.post(url, headers={"Content-Type":"application/json"}, data="{}", timeout=15)
        assert r.status_code in (401, 403), f"{ep} should require auth; got {r.status_code}"
