# Policy decision observability

This guide explains how the Prep city compliance services capture, persist, and visualise
policy evaluation activity from the Open Policy Agent (OPA) integration.

## Data flow

1. **FastAPI handler instrumentation** – the `/city/{city}/{state}/compliance-check`
   endpoint in `apps/city_regulatory_service/main.py` now wraps every OPA call with timing
   and error capture.
2. **Logging helper** – the helper in `prep/regulatory/policy_logging.py` normalises the
   request payload, computes a deterministic hash, trims long rationale/error strings, and
   writes a `PolicyDecision` ORM instance with duration converted from nanoseconds to
   milliseconds.
3. **Database persistence** – `prep/regulatory/models.py` defines the `policy_decisions`
   table, surfaced through `prep.models`. Alembic revision
   `2024110101_create_policy_decisions_table.py` provisions the table plus indexes on
   request hash, region/jurisdiction, and decision/created_at for fast slices.
4. **Observability** – Grafana dashboard `grafana/dashboards/sf_bay_area_policy_observability.json`
   visualises latency, deny rate, and jurisdiction volume for Bay Area traffic by querying
   the same table.

## Required configuration

- **Database** – run the Alembic migration to create the `policy_decisions` table. The
  ORM uses the shared SQLAlchemy `SessionLocal` so existing pooling and credentials apply.
- **OPA endpoints** – set `OPA_URL` (and optionally `OPA_PACKAGE_PATH`) for the city
  regulatory service. When unset, the service still records local fallback decisions so the
  telemetry table remains populated.
- **OpenTelemetry (optional)** – the helper in `apps/city_regulatory_service/otel.py`
  initialises a tracer once and falls back to a no-op tracer when `opentelemetry-sdk` is
  absent. Spans are emitted under the `policy.evaluate` name with region, jurisdiction, and
  package path attributes.

## Grafana import

1. Ensure the `prep-regulatory` datasource points to the operational database (or replica)
   containing the `policy_decisions` table.
2. Import the dashboard JSON from `grafana/dashboards/sf_bay_area_policy_observability.json`
   through Grafana's "Dashboards → Import" UI.
3. Validate that the latency, deny-rate, and jurisdiction panels render data for the
   selected time window.

## Key metrics

- **OPA latency (ms)** – average and p99 execution time for the policy package, grouped by
  minute.
- **Deny rate (%)** – percentage of policy evaluations returning `deny` over a rolling
  five-minute window.
- **Evaluations by jurisdiction** – aggregated counts of decisions per city to highlight
  spikes or ingestion gaps.

## Smoke test checklist

- Issue allow and deny requests against the compliance endpoint and confirm the response
  body still matches previous behaviour.
- Inspect the `policy_decisions` table to verify rows land with the correct `duration_ms`
  and trimmed rationale/error fields.
- Import the Grafana dashboard and ensure panels render against the populated dataset.
