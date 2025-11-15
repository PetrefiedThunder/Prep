# Post-MVP Domain Service Extraction Plan

## Context
The Prep platform has cleared MVP functionality for bookings, payments, and compliance screening, but the analytics suite, shared ORM layer, and compliance engines are still tightly coupled inside the monolith. High-severity defects take priority, so structural refactors must be staged to avoid destabilizing the launch surface.

## Guiding Principles
- **Bug backlog first:** No extraction work begins until all P0/P1 defects in `REMAINING_ISSUES_REPORT.md` are closed and validated in staging.
- **Domain boundaries:** Treat analytics, persistence (ORM), and compliance engines as separate bounded contexts with their own deployability targets.
- **Feature flag safety:** Any domain carved out must re-enter production behind explicit settings (see `ANALYTICS_ENDPOINTS_ENABLED`).

## Phase 0 – Stabilization (Weeks 0-2)
- Confirm zero open Sev-0/Sev-1 incidents across API and background workers.
- Capture operational metrics for analytics endpoints (latency, error rate) via `prep/monitoring` dashboards to define freeze thresholds.
- Audit shared ORM usage by generating a dependency graph from `prep/models/orm.py` to downstream services.

## Phase 1 – Analytics Service Extraction (Weeks 3-5)
- Finalize API contract for `/api/v1/analytics` and `/analytics/host/*` routes in `openapi.yaml`.
- Move FastAPI routers from `prep/analytics` into a dedicated `services/analytics_api` package with an internal client for the monolith.
- Stand up a read replica database dedicated to analytics workloads; sync via CDC or materialized views.
- Harden feature flags: default `ANALYTICS_ENDPOINTS_ENABLED` to `False` until the new service meets SLOs.

## Phase 2 – ORM Boundary (Weeks 5-7)
- Split `prep/models/orm.py` into schema-specific modules (bookings, kitchens, reviews) under `prep/models/domains/`.
- Introduce SQLAlchemy registry per module to enable future service-specific metadata.
- Replace direct ORM imports with repository interfaces in domain services (`prep/bookings`, `prep/kitchens`).
- Document migration strategy for alembic scripts and shared base classes.

## Phase 3 – Compliance Engines (Weeks 7-9)
- Wrap `dol_reg_compliance_engine` and sibling engines in a unified compliance facade (`services/compliance_core`).
- Expose compliance validations over internal gRPC/HTTP with explicit SLAs.
- Ensure configuration schemas live alongside each engine with schema validation enforced by CI.

## Phase 4 – Hardening & Decommission (Weeks 9-10)
- Run shadow traffic from the monolith to new services while keeping feature flags disabled.
- Execute load tests and regression suites recorded in `TROUBLESHOOTING.md` to validate parity.
- Decommission unused modules in the monolith once service SLOs are met and observability coverage is in place.

## Deliverables
- Signed-off RFCs for each phase with owners and exit criteria.
- Updated runbooks in `RUNBOOK.md` for analytics and compliance outage handling.
- Post-mortem templates capturing lessons learned for future extractions.

