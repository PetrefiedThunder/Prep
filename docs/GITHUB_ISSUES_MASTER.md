# GitHub Issues Master Plan - Ambiguity Remediation Sprint

This document contains all GitHub issues ready for creation, organized by Sprint and Epic.

## Milestones

Create these milestones first:
1. **Sprint 1: Golden Path + System Clarity**
2. **Sprint 2: Jurisdiction Clarity + MVP**
3. **Sprint 3: Data Model, Payments, Compliance Engine**
4. **Sprint 4: Observability + Cleanup**

## Labels

Create these labels:
- `epic-a-golden-path` - Golden Path Demo
- `epic-b-system-map` - System Map & Service Classification
- `epic-c-jurisdiction` - Jurisdiction Clarity
- `epic-d-mvp` - MVP Definition
- `epic-e-data-model` - Data Model & ERD Clarity
- `epic-g-payments` - Payments Architecture
- `epic-h-compliance` - Compliance Engine Architecture
- `epic-i-observability` - Observability & SLOs
- `epic-j-cleanup` - Cleanup & Repository Hygiene
- `sprint-1` - Sprint 1
- `sprint-2` - Sprint 2
- `sprint-3` - Sprint 3
- `sprint-4` - Sprint 4
- `documentation` - Documentation tasks
- `infrastructure` - Infrastructure tasks
- `testing` - Testing tasks

---

## Sprint 1: Golden Path + System Clarity

### Epic A: Golden Path Demo
**Goal:** One reproducible, end-to-end working flow covering LA Vendor → Compliance → Booking.

#### Issue A1: Create Golden Path Documentation
**Title:** Create Golden Path Documentation
**Milestone:** Sprint 1: Golden Path + System Clarity
**Labels:** `epic-a-golden-path`, `sprint-1`, `documentation`

**Description:**
Create comprehensive documentation for the Golden Path demo flow that demonstrates the complete LA Vendor → Compliance → Booking scenario.

**Acceptance Criteria:**
- [ ] Create docs/GOLDEN_PATH_DEMO.md
- [ ] Define LA Vendor → Compliance → Booking scenario
- [ ] Add step-by-step commands (clone, setup, compose)
- [ ] Include expected outputs and success criteria
- [ ] Add troubleshooting section

**Epic Context:**
Part of Epic A: Golden Path Demo - establishing one reproducible, end-to-end working flow.

---

#### Issue A2: Create Golden Path Fixtures
**Title:** Create Golden Path Fixtures
**Milestone:** Sprint 1: Golden Path + System Clarity
**Labels:** `epic-a-golden-path`, `sprint-1`, `testing`

**Description:**
Create sample data fixtures to support the Golden Path demo, enabling consistent and reproducible testing of the LA vendor flow.

**Acceptance Criteria:**
- [ ] Create vendor license sample data
- [ ] Create facility sample data
- [ ] Create LA jurisdiction ruleset fixture
- [ ] Add fixture loading scripts
- [ ] Document fixture usage in GOLDEN_PATH_DEMO.md

**Epic Context:**
Part of Epic A: Golden Path Demo - providing test data for the end-to-end flow.

---

#### Issue A3: Service Boot Consistency
**Title:** Fix Service Boot Consistency Issues
**Milestone:** Sprint 1: Golden Path + System Clarity
**Labels:** `epic-a-golden-path`, `sprint-1`, `infrastructure`

**Description:**
Ensure all services boot consistently and reliably during docker compose up, with proper environment variable configuration.

**Acceptance Criteria:**
- [ ] Verify all required env vars exist across services
- [ ] Update .env.example with missing variables
- [ ] Fix failing services during docker compose up
- [ ] Add service health checks to docker-compose.yml
- [ ] Document service dependencies

**Epic Context:**
Part of Epic A: Golden Path Demo - ensuring reliable service startup for demos.

---

#### Issue A4: Observability for Golden Path
**Title:** Add Observability for Golden Path Demo
**Milestone:** Sprint 1: Golden Path + System Clarity
**Labels:** `epic-a-golden-path`, `sprint-1`, `infrastructure`, `testing`

**Description:**
Implement observability and monitoring for the Golden Path flow to track events and validate the compliance → booking pipeline.

**Acceptance Criteria:**
- [ ] Add Grafana dashboard for Golden Path event flow
- [ ] Add log tracing for compliance → booking
- [ ] Add pytest -m golden_path regression test
- [ ] Create alert rules for Golden Path failures
- [ ] Document monitoring setup

**Epic Context:**
Part of Epic A: Golden Path Demo - providing visibility into the end-to-end flow.

---

### Epic B: System Map & Service Classification
**Goal:** Make repo instantly understandable to new engineers.

#### Issue B1: Create SYSTEM_MAP.md
**Title:** Create System Map Documentation
**Milestone:** Sprint 1: Golden Path + System Clarity
**Labels:** `epic-b-system-map`, `sprint-1`, `documentation`

**Description:**
Create a comprehensive system map that documents all services, their purposes, owners, and current status.

**Acceptance Criteria:**
- [ ] List all services with purpose and owners
- [ ] Assign statuses: GA, Beta, Experimental
- [ ] Create service dependency diagram
- [ ] Link System Map from README
- [ ] Add service communication patterns

**Epic Context:**
Part of Epic B: System Map & Service Classification - making the repo understandable.

---

#### Issue B2: Add Service Status Labels
**Title:** Implement Service Status Classification
**Milestone:** Sprint 1: Golden Path + System Clarity
**Labels:** `epic-b-system-map`, `sprint-1`, `documentation`

**Description:**
Add status labels to all services and reorganize the repository structure based on service maturity.

**Acceptance Criteria:**
- [ ] Add #Status to every service README
- [ ] Move abandoned services to /experimental/
- [ ] Update top-level README with status table
- [ ] Create migration guide for moved services
- [ ] Update docker-compose files to reflect structure

**Epic Context:**
Part of Epic B: System Map & Service Classification - clarifying service maturity.

---

## Sprint 2: Jurisdiction Clarity + MVP

### Epic C: Jurisdiction Clarity
**Goal:** Explicit city-by-city regulatory coverage.

#### Issue C1: Create JURISDICTION_STATUS.md
**Title:** Document Jurisdiction Coverage Status
**Milestone:** Sprint 2: Jurisdiction Clarity + MVP
**Labels:** `epic-c-jurisdiction`, `sprint-2`, `documentation`

**Description:**
Create comprehensive documentation of regulatory coverage for each jurisdiction (city).

**Acceptance Criteria:**
- [ ] List cities with coverage completeness
- [ ] Document regression test status per city
- [ ] Document issuer API/portal availability
- [ ] Add compliance requirements per city
- [ ] Include last updated dates

**Epic Context:**
Part of Epic C: Jurisdiction Clarity - making regulatory coverage explicit.

---

#### Issue C2: Add Jurisdiction Regression Tests
**Title:** Implement Per-Jurisdiction Regression Tests
**Milestone:** Sprint 2: Jurisdiction Clarity + MVP
**Labels:** `epic-c-jurisdiction`, `sprint-2`, `testing`

**Description:**
Create comprehensive regression test suites for LA and SF jurisdictions.

**Acceptance Criteria:**
- [ ] Add LA compliance tests
- [ ] Add SF compliance tests
- [ ] Add fixture directories for each city
- [ ] Create test data for each jurisdiction
- [ ] Add CI pipeline for jurisdiction tests

**Epic Context:**
Part of Epic C: Jurisdiction Clarity - validating regulatory logic per city.

---

#### Issue C3: Define MVP Jurisdiction Scope
**Title:** Define and Implement MVP Jurisdiction Scope
**Milestone:** Sprint 2: Jurisdiction Clarity + MVP
**Labels:** `epic-c-jurisdiction`, `sprint-2`, `documentation`

**Description:**
Clearly define the MVP jurisdiction scope (LA + SF) and adjust infrastructure accordingly.

**Acceptance Criteria:**
- [ ] Define MVP = LA + SF
- [ ] Disable other cities in compose.mvp.yml
- [ ] Cross-link with MVP_SCOPE.md
- [ ] Update documentation to reflect MVP scope
- [ ] Add feature flags for non-MVP jurisdictions

**Epic Context:**
Part of Epic C: Jurisdiction Clarity - focusing on MVP jurisdictions.

---

### Epic D: MVP Definition
**Goal:** Clarify what is real, what is future, and what to ignore.

#### Issue D1: Create MVP_SCOPE.md
**Title:** Document MVP Scope and Boundaries
**Milestone:** Sprint 2: Jurisdiction Clarity + MVP
**Labels:** `epic-d-mvp`, `sprint-2`, `documentation`

**Description:**
Create clear documentation defining what is included, excluded, and planned for future in the MVP.

**Acceptance Criteria:**
- [ ] Define Included in MVP
- [ ] Define Excluded from MVP
- [ ] Define Future Scope
- [ ] Add roadmap timeline
- [ ] Link to architecture decision records (ADRs)

**Epic Context:**
Part of Epic D: MVP Definition - establishing clear product boundaries.

---

#### Issue D2: Repository Hygiene for MVP
**Title:** Reorganize Repository for MVP Focus
**Milestone:** Sprint 2: Jurisdiction Clarity + MVP
**Labels:** `epic-d-mvp`, `sprint-2`, `infrastructure`

**Description:**
Restructure the repository to clearly separate MVP services from experimental/future work.

**Acceptance Criteria:**
- [ ] Move non-MVP services to /experimental/
- [ ] Disable non-MVP services in compose.mvp.yml
- [ ] Add MVP-only CI test
- [ ] Update README with MVP structure
- [ ] Create migration guide

**Epic Context:**
Part of Epic D: MVP Definition - physically organizing code to match MVP scope.

---

## Sprint 3: Data Model, Payments, Compliance Engine

### Epic E: Data Model & ERD Clarity
**Goal:** Make the data model explicit and consistent across services.

#### Issue E1: Generate Entity Relationship Diagrams
**Title:** Create ERD Documentation
**Milestone:** Sprint 3: Data Model, Payments, Compliance Engine
**Labels:** `epic-e-data-model`, `sprint-3`, `documentation`

**Description:**
Generate comprehensive Entity Relationship Diagrams for all core entities in the system.

**Acceptance Criteria:**
- [ ] Create ERD diagrams for core entities
- [ ] Add docs/ERD/ERD.png
- [ ] Document relationships clearly
- [ ] Add entity descriptions
- [ ] Link ERD from main documentation

**Epic Context:**
Part of Epic E: Data Model & ERD Clarity - visualizing data relationships.

---

#### Issue E2: Create DATA_MODEL.md
**Title:** Document Complete Data Model
**Milestone:** Sprint 3: Data Model, Payments, Compliance Engine
**Labels:** `epic-e-data-model`, `sprint-3`, `documentation`

**Description:**
Create comprehensive documentation of the data model, including entities, relationships, and consistency rules.

**Acceptance Criteria:**
- [ ] Document each core entity
- [ ] Document ID consistency rules
- [ ] Document cross-service entity consumption
- [ ] Add data validation rules
- [ ] Include migration guidelines

**Epic Context:**
Part of Epic E: Data Model & ERD Clarity - documenting data structures.

---

#### Issue E3: Add Migration Consistency Tests
**Title:** Implement Data Model Consistency Tests
**Milestone:** Sprint 3: Data Model, Payments, Compliance Engine
**Labels:** `epic-e-data-model`, `sprint-3`, `testing`

**Description:**
Create automated tests to validate data model consistency across services and languages.

**Acceptance Criteria:**
- [ ] Validate Postgres schema matches entity model
- [ ] Add mismatch test between Node and Python services
- [ ] Add migration validation tests
- [ ] Create schema drift detection
- [ ] Add CI integration

**Epic Context:**
Part of Epic E: Data Model & ERD Clarity - ensuring model consistency.

---

### Epic G: Payments Architecture
**Goal:** Clarify Stripe Connect, payouts, ledger, and platform fees.

#### Issue G1: Create PAYMENTS_ARCHITECTURE.md
**Title:** Document Payments Architecture
**Milestone:** Sprint 3: Data Model, Payments, Compliance Engine
**Labels:** `epic-g-payments`, `sprint-3`, `documentation`

**Description:**
Create comprehensive documentation of the payments architecture, including Stripe Connect integration and fee structures.

**Acceptance Criteria:**
- [ ] Document Stripe Connect workflow
- [ ] Define vendor→connected account mapping
- [ ] Define platform fees and payout logic
- [ ] Add payment flow diagrams
- [ ] Document error handling and retries

**Epic Context:**
Part of Epic G: Payments Architecture - clarifying payment flows.

---

#### Issue G2: Add Pricing and Fees Tests
**Title:** Implement Payments and Fees Testing
**Milestone:** Sprint 3: Data Model, Payments, Compliance Engine
**Labels:** `epic-g-payments`, `sprint-3`, `testing`

**Description:**
Create comprehensive test suite for payment calculations, fees, and ledger operations.

**Acceptance Criteria:**
- [ ] Add fee calculation tests
- [ ] Add pricing simulation fixtures
- [ ] Validate ledger write logic
- [ ] Test payout scenarios
- [ ] Add integration tests with Stripe

**Epic Context:**
Part of Epic G: Payments Architecture - validating payment logic.

---

### Epic H: Compliance Engine Architecture
**Goal:** Make regulatory logic predictable, data-driven, testable.

#### Issue H1: Document Compliance Engine
**Title:** Create Compliance Engine Documentation
**Milestone:** Sprint 3: Data Model, Payments, Compliance Engine
**Labels:** `epic-h-compliance`, `sprint-3`, `documentation`

**Description:**
Document the compliance engine architecture, rule formats, and decision logic.

**Acceptance Criteria:**
- [ ] Create regengine/README.md
- [ ] Document rule formats (YAML or Python DSL)
- [ ] Document decision tree / DAG
- [ ] Add rule authoring guide
- [ ] Include examples for LA and SF

**Epic Context:**
Part of Epic H: Compliance Engine Architecture - documenting regulatory logic.

---

#### Issue H2: Refactor to Data-Driven Rules
**Title:** Convert Hard-Coded Rules to Data-Driven Configuration
**Milestone:** Sprint 3: Data Model, Payments, Compliance Engine
**Labels:** `epic-h-compliance`, `sprint-3`, `infrastructure`

**Description:**
Refactor compliance engine to use data-driven rule configuration instead of hard-coded logic.

**Acceptance Criteria:**
- [ ] Convert hard-coded rules to configs
- [ ] Add common validation interface
- [ ] Create rule DAG visualizations for LA + SF
- [ ] Implement rule versioning
- [ ] Add rule validation tooling

**Epic Context:**
Part of Epic H: Compliance Engine Architecture - making rules maintainable.

---

#### Issue H3: Add Compliance Regression Tests
**Title:** Implement Compliance Engine Test Matrix
**Milestone:** Sprint 3: Data Model, Payments, Compliance Engine
**Labels:** `epic-h-compliance`, `sprint-3`, `testing`

**Description:**
Create comprehensive test matrix for compliance rules across all jurisdictions.

**Acceptance Criteria:**
- [ ] Build compliance test matrix
- [ ] Add failing→passing rule tests
- [ ] Link tests directly to Golden Path
- [ ] Add edge case coverage
- [ ] Create regression test suite

**Epic Context:**
Part of Epic H: Compliance Engine Architecture - validating regulatory logic.

---

## Sprint 4: Observability + Cleanup

### Epic I: Observability & SLOs
**Goal:** Define and monitor reliability of compliance, booking, payouts.

#### Issue I1: Define Service Level Objectives
**Title:** Document SLOs for Core Services
**Milestone:** Sprint 4: Observability + Cleanup
**Labels:** `epic-i-observability`, `sprint-4`, `documentation`

**Description:**
Define and document Service Level Objectives for all core services.

**Acceptance Criteria:**
- [ ] Create docs/SLO.md
- [ ] Define latency budgets
- [ ] Define error budgets
- [ ] Set availability targets
- [ ] Document measurement methodology

**Epic Context:**
Part of Epic I: Observability & SLOs - establishing reliability standards.

---

#### Issue I2: Implement Observability Dashboards
**Title:** Create Grafana Dashboards for SLOs
**Milestone:** Sprint 4: Observability + Cleanup
**Labels:** `epic-i-observability`, `sprint-4`, `infrastructure`

**Description:**
Implement comprehensive Grafana dashboards to monitor SLOs and service health.

**Acceptance Criteria:**
- [ ] Add Grafana SLO dashboards
- [ ] Add service uptime metrics
- [ ] Create alert templates
- [ ] Implement alert routing
- [ ] Document dashboard usage

**Epic Context:**
Part of Epic I: Observability & SLOs - monitoring service reliability.

---

### Epic J: Cleanup & Repository Hygiene
**Goal:** Remove ambiguity caused by drift and unused folders.

#### Issue J1: Repository Cleanup
**Title:** Clean Up Repository Structure
**Milestone:** Sprint 4: Observability + Cleanup
**Labels:** `epic-j-cleanup`, `sprint-4`, `infrastructure`

**Description:**
Clean up repository by removing outdated code, organizing prototypes, and establishing ownership.

**Acceptance Criteria:**
- [ ] Move prototypes to /experimental/
- [ ] Delete outdated or duplicate docs
- [ ] Add CODEOWNERS
- [ ] Remove dead code
- [ ] Update .gitignore

**Epic Context:**
Part of Epic J: Cleanup & Repository Hygiene - reducing technical debt.

---

#### Issue J2: Standardize Service Documentation
**Title:** Create Consistent Service Documentation
**Milestone:** Sprint 4: Observability + Cleanup
**Labels:** `epic-j-cleanup`, `sprint-4`, `documentation`

**Description:**
Ensure every service has consistent, comprehensive documentation following a standard template.

**Acceptance Criteria:**
- [ ] Add README to every service
- [ ] Link each README to System Map
- [ ] Add semantic version tagging
- [ ] Create documentation template
- [ ] Validate documentation completeness

**Epic Context:**
Part of Epic J: Cleanup & Repository Hygiene - standardizing documentation.

---

## Summary

**Total Issues:** 24
**Total Sprints:** 4
**Total Epics:** 9

### Issue Distribution by Sprint:
- Sprint 1: 6 issues (Epics A, B)
- Sprint 2: 5 issues (Epics C, D)
- Sprint 3: 9 issues (Epics E, G, H)
- Sprint 4: 4 issues (Epics I, J)

### Issue Distribution by Epic:
- Epic A (Golden Path): 4 issues
- Epic B (System Map): 2 issues
- Epic C (Jurisdiction): 3 issues
- Epic D (MVP): 2 issues
- Epic E (Data Model): 3 issues
- Epic G (Payments): 2 issues
- Epic H (Compliance): 3 issues
- Epic I (Observability): 2 issues
- Epic J (Cleanup): 2 issues

---

## Next Steps

1. Create the milestones in GitHub
2. Create the labels in GitHub
3. Use the automation script (see create_github_issues.py) to create all issues
4. Review and adjust issue assignments
5. Begin Sprint 1 execution
