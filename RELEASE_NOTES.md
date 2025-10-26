# Prep v0.1.0 — Orchestration Foundation (2025-10-26)

## Highlights
- **Enterprise Orchestration Layer** for multi-domain compliance
- **Compliance Engines:** GDPR/CCPA and AML/KYC (pluggable)
- **AI Agent Framework** with Safety + Validation gates
- **Unified Data Pipeline** (ingesters + transformers)
- **Audit Trail** primitives and **Observability** scaffolds
- **Zero-Trust Security** primitives

## Developer Experience
- Restored **`pyproject.toml`** with installable package + dev extras
- New **Python CI** with lint (`ruff`), type (`mypy`), tests (`pytest`)
- **Mass-deletion guard** for safer reviews
- **SQLite-portable GUID** type to avoid UUID dialect issues

## Tests
- New **orchestration smoke test** validates multi-domain run + aggregate risk

## Breaking Changes
- Legacy marketplace modules removed; see `SAFE_DELETE.md`
- Old CI workflow replaced with Python-focused pipeline

## Next (0.1.1)
- Evidence Vault v0 (write-once + content hash)
- JSON-Schema validation for engine outputs
- Human-in-the-Loop review queue
- `/healthz` and `/metrics` endpoints
