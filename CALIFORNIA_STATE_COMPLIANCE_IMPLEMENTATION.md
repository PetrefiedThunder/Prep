# California State Compliance Layer Implementation

## Overview

The California state layer extends Prep's jurisdictional stack between the federal core and the existing city modules. It harmonizes requirements from the **California Retail Food Code (CalCode)**, **California Department of Public Health (CDPH)** programs, and statewide licensing frameworks, then exposes those rules through the same service and data patterns used by the city layer.

This plan reuses the operational scaffolding delivered in `CITY_COMPLIANCE_IMPLEMENTATION.md` and maps California's state-wide obligations into reusable schemas that downstream city and facility checks can inherit.

---

## Architecture & Components

```
apps/state_regulatory_service/
├── california/
│   ├── main.py                     # FastAPI endpoints mounted under /state/ca
│   ├── models.py                   # Pydantic models for CA requirements
│   ├── etl.py                      # CalCode + CDPH ingestion pipeline
│   ├── permit_registry.py          # Statewide permit index & lookups
│   ├── enforcement_agencies.py     # CDPH, CalEPA, Cal/OSHA integrations
│   ├── tasks.py                    # Orchestrated refresh jobs
│   ├── __init__.py
│   └── tests/
│       ├── test_california_service.py
│       └── test_state_engine_bridge.py
│
prep/compliance/state/
└── california_state_engine.py      # Jurisdictional rules + scoring

apps/city_regulatory_service/
└── adapters/california_bridge.py   # Shares logic with Los Angeles & San Francisco modules

jobs/state_regulation_refresh.py    # Nightly ETL entrypoint

schemas/state/california/
├── requirement.schema.json
├── permit.schema.json
└── enforcement_agency.schema.json

infra/terraform/state-layer/
└── california_state_service.tf     # Optional infra module for deployment
```

### Data Sources
- **CalCode** sections 113700-114439 (current year download)
- **CDPH Food and Drug Branch** facility licensing catalog
- **California Secretary of State** business registration verification
- **Cal/OSHA** safety mandates for commercial kitchens
- **CalEPA** hazardous waste & grease interceptor guidelines

### Integration Touchpoints
- Extends `prep/compliance/orchestration.py` registration table with `ComplianceDomain.STATE_CA`
- Shares caching layer with `apps/city_regulatory_service` via Redis namespace `compliance:state:ca`
- Publishes state-wide canonical requirements consumed by Los Angeles & San Francisco city adapters

---

## Implementation Plan & Estimates

| # | Work Item | Files / Modules | Estimate | Owner | Notes |
|---|-----------|-----------------|----------|-------|-------|
| 1 | Data model scaffolding | `prep/compliance/state/california_state_engine.py`, `schemas/state/california/*.json` | 6h | Backend | Create requirement, permit, enforcement schemas mirroring city JSON contracts.
| 2 | ETL ingestion pipeline | `apps/state_regulatory_service/california/etl.py`, `data/state/california/raw/*.csv` | 10h | Data Eng | Parse CalCode XML/CSV, normalize into SQLite tables.
| 3 | API surface | `apps/state_regulatory_service/california/main.py`, `models.py` | 8h | Backend | CRUD + compliance check endpoints under `/state/ca/*`.
| 4 | City bridge | `apps/city_regulatory_service/adapters/california_bridge.py` | 4h | Backend | Reuse state-normalized data for Los Angeles & San Francisco.
| 5 | Scheduler + jobs | `jobs/state_regulation_refresh.py`, `apps/state_regulatory_service/california/tasks.py` | 3h | DevOps | Nightly sync & alerting hooks.
| 6 | Tests & QA | `apps/state_regulatory_service/california/tests/*`, `tests/e2e/test_state_integration.py` | 6h | QA | Contract + E2E tests across state + city engine.
| 7 | Deployment artifacts | `infra/terraform/state-layer/california_state_service.tf`, `Dockerfile.state` | 4h | DevOps | Container & Terraform module aligning with existing services.

**Total:** ~41 hours (one engineering week with QA overlap)

---

## Execution Guidance

1. **Schema First:** Draft JSON schemas in `schemas/state/california/` and validate them against CalCode samples using `scripts/validate_schema.py`.
2. **ETL Alignment:** Leverage the existing SQLite pattern (`prep_city_regulations.sqlite`) by introducing `data/state/california/prep_state_california.sqlite` with analogous tables (`state_requirements`, `state_permits`, `state_enforcement_contacts`).
3. **Service Parity:** Mirror the route structure of the city service (healthz, list, detail, compliance-check) to ensure the web dashboard can swap city/state toggles with minimal frontend work.
4. **Bridge Module:** Expose helper methods `get_state_requirement(state_code, requirement_type)` so city adapters can enrich local ordinances with state prerequisites.
5. **Testing Strategy:**
   - Unit tests for schema validation and ETL transforms
   - Integration tests hitting `/state/ca/compliance-check`
   - Snapshot tests comparing Los Angeles city rules before/after state enrichment
6. **Operational Hooks:** Add Prometheus metrics (`state_california_requirements_loaded`, `state_california_compliance_checks_total`) and alerting thresholds mirroring the federal layer playbook.

---

## Rollout Checklist
- [ ] Schemas validated with 10 sample facilities across CA counties
- [ ] ETL job scheduled in Airflow (`dags/state_california_refresh.py`)
- [ ] API deployed to staging (`state-ca.staging.prep.run`)
- [ ] Dashboard toggle enabled for California state layer
- [ ] Documentation published in `docs/compliance_layers.md`
- [ ] Customer advisory review with CA pilot kitchens

