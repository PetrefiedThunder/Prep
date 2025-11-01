# Constraints for Code Generation

General
- Language: Python 3.11 for services/tests; Rego for OPA
- Strict typing: add type hints and pydantic validation for all new public functions
- No secrets in code, config, or tests; use env vars only
- Idempotent migrations: never edit historic Alembic revisions
- CI runs ``make etl.validate``; keep fee schedule validators passing locally

Compliance/OPA
- All new jurisdictions implement: ingest.py, validate.py, policy.rego
- Policies must expose decision path `allow` with explainable rationale
- Golden tests required under `tests/policy/<region>`

Observability
- Every decision writes to `policy_decisions` (no raw input; sha256 only)
- OpenTelemetry attributes: region, jurisdiction, package_path, latency_ms

Docs
- Update `docs/observability/policy_decisions.md` if schema changes
