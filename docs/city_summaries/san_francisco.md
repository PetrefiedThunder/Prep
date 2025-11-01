**Prep — San Francisco Compliance Summary (Operational Readiness)**
**Scope:** Short-term commercial kitchen rentals within SF jurisdiction.

**Required Permits & Proofs**

* Shared Kitchen Facility (SF Health Code §6.15) — **active + unexpired**
* Fire inspection & Ventilation certification — **uploaded reports**

* Zoning: confirm district & **neighborhood notice** where required (e.g., NC-3, PDR)
* Insurance: COI naming **“City and County of San Francisco”**; General Liability ≥ $1M / Aggregate ≥ $2M

**Booking Gate (System-Enforced)**

* Hard DENY if: shared-kitchen permit missing/expired; insurance AI string mismatch; inspection scheduled overlap; quiet-hours breach.
* Conditions if: grease service overdue; ADA required but not available; daily hour cap approaching.

**Fees/Taxes**

* **TOT 14%** applied to base, cleaning, platform fee (itemized at checkout).
* **Deposit**: min $100; held ≤ 72h post-booking (auto-release unless incident).

**Safety & Incident**

* Health hotline on file; outbreak trigger auto-notifies and logs time.
* Inspection failure **auto-unlists** facility until updated report passes.

**Records & Renewals**

* Permit expirations tracked with reminders (30/7/1 days).
* Neighborhood complaints logged and triaged; quiet-hour threshold = soft block.

**Status:** Rule pack + fixtures implemented; golden tests cover pass/fail/conditions.

---

### Remaining Gaps for Full Market Launch

* **Regulatory depth is incomplete.** The current rule pack mirrors a generic California implementation and does **not encode San Francisco Health Code Article 11 requirements** (commercial-grade equipment attestations, grease trap maintenance logs, pest control verification, composting plans, etc.). Without these checks, the compliance engine cannot deliver legally binding pass/fail decisions for SF operators.
* **Financial compliance is missing.** Pricing flows omit **SF Gross Receipts (1.5%), Transient Occupancy (14%), and Tourism Improvement (0.25%) taxes**. These must be collected, itemized, and remitted in the booking lifecycle alongside platform fees.
* **City validation integrations are stubs.** There are no live hooks for **SF Department of Public Health permit verification, Business Registration Certificate lookups, zoning confirmations, or fire inspection records**. Launch readiness demands real-time validations + monitoring for these endpoints.
* **Insurance thresholds are under-scoped.** SF requires **$2M general liability aggregate, $1M employment practices liability, and conditional liquor/auto coverage**, which exceed the current generic $1M policy checks.

### Suggested Implementation Phases

1. **Foundation (Weeks 1–4)**
   * Encode Article 11 + neighborhood-specific requirements into the compliance engine.
   * Extend pricing service with the full SF tax stack and reporting outputs.
   * Introduce SF-specific insurance policy validators.
2. **Integration (Weeks 5–8)**
   * Ship API clients for SF Health, Business, Fire, and Planning datasets.
   * Wire booking + onboarding flows to those validators with actionable error messaging.
   * Stand up dashboards/alerts for permit expirations, failed validations, and overdue inspections.
3. **Optimization (Weeks 9–12)**
   * Layer in neighborhood overrides (Mission, Financial District, Chinatown, etc.) and seasonal policy deltas (holiday hour extensions, summer outdoor cooking, rainy-season grease cadence).
   * Generate quarterly tax remittance packets and compliance analytics tailored to SF regulators.

### Risk Snapshot

* **High:** Regulatory non-compliance (launch blocked), tax under-remittance (fines/penalties), insufficient insurance coverage (liability exposure).
* **Medium:** Operator trust + market fit if validations feel manual or inconsistent.
* **Low:** Core architecture is extensible; existing rule-pack framework can absorb SF-specific modules.
