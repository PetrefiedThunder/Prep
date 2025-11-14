# Testing & Validation Program

> **Status:** Draft

This document captures the comprehensive, end-to-end testing and validation strategy for Prep's integration framework. It is structured so that automated agents (including Codex) and CI/CD pipelines can execute it autonomously. The plan is organized into guardrails, test categories, tooling, representative assertions, and promotion rules.

---

## 0. Global Test Guardrails

* **Branch gates:** `lint → unit → mutation → integration(contract) → e2e(sandbox) → perf smoke → sec scan → IaC policy` (all stages must pass before merge).
* **Coverage floors:** unit ≥ 85%, mutation ≥ 70% killed mutants, integration ≥ 80% path, e2e critical flows 100%.
* **Idempotency & retries:** every write path validated for safe retries and deduplication keys.
* **Deterministic seeds:** eliminate flake via seed pinning and Testcontainers.
* **Observability invariants:** every service exports health probes and SLIs; failing SLI fails the suite.

---

## 1. Static Analysis & Build Hygiene

**Goal:** catch defects pre-runtime.

* **Linters & formatters:** ESLint/Prettier (Node), Ruff/Black (Python).
* **Types & schemas:** TypeScript strict mode; Pydantic for FastAPI; OpenAPI diff checks.
* **Security linters:** Semgrep, Bandit (Python), npm-audit/yarn-audit.
* **Secret scanning:** Gitleaks/detect-secrets; block on leak.
* **Dependency health:** Snyk/Trivy SCA; deny known vulnerabilities with CVSS ≥ 7.0.

**Pass gate:** zero critical/high issues; type check clean.

---

## 2. Unit Tests (Logic & Edge Cases)

**Goal:** full function-level assurance.

* **Connector SDK:** auth flows, webhook verification, backoff/retry, rate-limit handling, clock skew, idempotency keys, signature replay defense.
* **Integration Registry:** CRUD + RBAC, invalid state transitions, soft-delete, foreign key integrity to User/Kitchen.
* **Inventory microservice:** FIFO calculations, negative stock protection, expiry windows, timezone rollovers, partial transfers, transactional rollbacks.
* **Booking/Payments:** atomicity, Stripe idempotency, currency minor units, rounding, proration, refund/chargeback hooks.
* **PDF manifest builder:** deterministic fonts/layout, pagination, international glyph coverage.
* **Utilities:** time math, UUIDs, monotonic clocks, ISO8601 parsing, big-number money math.

**Tooling:** Jest + ts-jest; PyTest + Hypothesis (property-based).

**Pass gate:** coverage ≥ 85%; property invariants hold for 10k trials per suite.

---

## 3. Mutation Testing

**Goal:** ensure unit tests actually catch defects.

* **Scope:** SDK core, reconciliation engine, ledger classifiers, tax mappers, compliance validators.
* **Tooling:** Stryker (TypeScript), mutmut (Python).
* **Pass gate:** mutation score ≥ 70% (target 80% over time).

---

## 4. Contract & Integration Tests

**Goal:** validate each connector against a stable contract and sandbox APIs.

* **Pact contracts:** Square, Toast, MarketMan, Apicbase, DoorDash Drive, Uber Direct, QuickBooks, Xero, Avalara, Onfleet, Shopify, TikTok Shop, Square KDS, QSR Automations, Oracle Simphony.
* **Testcontainers:** spin Postgres, Redis/Kafka, MinIO (S3), WireMock per connector.
* **Failure modes:** 401/403, 429 (rate limit), 5xx with jitter, malformed payload, out-of-order webhooks, duplicated events, signature mismatch, TLS errors, DNS failover.
* **Idempotency tests:** resend webhooks; verify single state transition.
* **Clock skew:** ±10 minutes & DST boundaries.

**Pass gate:** 100% contract interactions satisfied; duplicates do not double-apply.

---

## 5. End-to-End (Sandbox) Flows

**Goal:** simulate real usage across services.

**Critical paths:**

1. **Delivery-Only Kitchen:** create kitchen → renter books → connect DoorDash Drive → place order → courier handoff (QR) → proof stored → PDF manifest generated.
2. **POS Reconciliation:** ingest Square + Toast → nightly reconcile → GAAP ledger entry → accounting sync to QuickBooks/Xero.
3. **Inventory Marketplace:** goods arrive (MarketMan) → stock increases → recipe usage (Apicbase) → expiry alert → borrow transfer → audit trail.
4. **Dynamic Pricing:** SpaceOptimizer discounts idle slot → renter books discounted window → invoice matches policy → Avalara taxes applied.
5. **Incident & Rollback:** connector outage → retry/backoff → circuit opens → alert fired → graceful degradation (cache or queue) → resumes with at-least-once semantics, no double-book.

**UI E2E:** Playwright + axe-core (see accessibility section).

**Pass gate:** all five flows pass; no orphaned records; logs/metrics present.

---

## 6. Performance & Scalability

**Goal:** validate SLAs and headroom.

* **Load models (k6/Locust):** API p95 < 300 ms at 1k RPS gateway (bursts 3k); webhook fan-in 10k/hour with 0% loss; reconciliation 1M transactions in < 15 min.
* **Soak:** 24h run at 60% peak; detect memory leaks.
* **Spike:** 10× burst on delivery status webhooks.
* **Latency budgets:** network jitter ±200 ms, packet loss 1%, ensure retries don’t cascade.

**Pass gate:** SLOs met; zero error amplification; GC and heap stable.

---

## 7. Chaos & Resilience

**Goal:** fail gracefully.

* **Fault injection:** Toxiproxy/Chaos Mesh on connectors (latency, drop, corrupt).
* **Infra kills:** pod eviction, node restart, Kafka partition loss, Postgres primary failover.
* **Replay & duplication:** ordered/unordered webhooks; exactly-once processing validated via dedupe keys.
* **Partial outage drills:** accounting down, still accept bookings; delivery down, queue orders.

**Pass gate:** no data loss; alerts trigger; RTO ≤ 15 min per component.

---

## 8. Security Testing

**Goal:** trust boundaries enforced.

* **DAST:** OWASP ZAP/Burp automated against staging.
* **AuthZ tests:** tenant isolation, role matrix (Admin/Host/Renter/Read-only).
* **Webhook signing:** HMAC validation, timestamp freshness window, replay detection.
* **JWT hardening:** `alg=none` refusal, exp/nbf checks, key rotation.
* **CORS & CSRF:** strict origins; anti-CSRF on dashboard.
* **Secrets:** runtime scan; env var policy; no secrets in logs.
* **Container/OS:** Trivy image scan; Dockle; non-root user; minimal base.
* **Dependency exploits:** pinned versions; allowlist for transitive highs only with compensating controls.

**Pass gate:** zero criticals; highs only with explicit waiver and expiry.

---

## 9. Privacy, Data Governance & Compliance

**Goal:** legal and ethical handling of data.

* **PII discovery:** Gitleaks + custom detectors; block builds on PII in repo.
* **Data tagging:** schema fields labeled (PII/Sensitive/Public); lineage tracked.
* **GDPR/CCPA flows:** export, delete, correct; right-to-be-forgotten across OLTP + data lake.
* **Consent & minimization:** connectors only fetch scoped data; deny overscoped requests.
* **Audit logs:** immutable append-only; administrator access trails.
* **Cryptography:** TLS 1.2+; at-rest keys managed; envelope encryption for documents.

**Pass gate:** DSR end-to-end < 30 days simulated; audit trails complete.

---

## 10. Data Quality & Analytics

**Goal:** trustworthy insights.

* **Great Expectations/Deequ checks:** not-null, ranges, referential integrity, uniqueness, currency precision, time monotonicity for events.
* **CDC validation:** schema registry & backward compatibility; drift alerts.
* **Reconciliation truth sets:** synthetic golden data to compare accounting exports.

**Pass gate:** 100% critical expectations green; schema compatibility maintained.

---

## 11. Accessibility (A11y) & UX Robustness

**Goal:** inclusive, resilient UI.

* **Automated checks:** axe-core + Lighthouse CI (a11y ≥ 95).
* **Keyboard navigation & screen reader:** tab order, ARIA roles, focus traps.
* **Contrast & color blindness:** WCAG AA minimum validated.
* **Offline/PWA:** network loss while booking; state persistence & replay.
* **Localization:** number/date formats, RTL sanity, long text overflow.

**Pass gate:** all critical a11y issues resolved; PWA passes offline flows.

---

## 12. Internationalization & Time/Locale Edge Cases

**Goal:** temporal correctness at scale.

* **DST transitions:** bookings across DST start/end; accounting cutoff integrity.
* **Leap second/minute & leap year:** parsers and schedulers.
* **Timezones:** kitchen timezone vs renter timezone vs data lake UTC consistency.
* **Currencies:** multi-currency ingest, decimal vs 0-decimal (e.g., JPY), rounding.

**Pass gate:** sums and invoices equal in native plus reporting currency.

---

## 13. ML: SpaceOptimizer & Anomaly Detection

**Goal:** safe and effective recommendations.

* **Reproducibility:** fixed seeds; same input → same plan.
* **Performance:** acceptance rate, uplift on utilization, regret bounds simulated.
* **Fairness & bias:** no systematic suppression of low-volume renters/hosts unless policy-backed.
* **Drift & data leakage:** EvidentlyAI monitors; alarming thresholds.
* **Fail-safe:** if model unavailable, rule-based fallback.

**Pass gate:** defined KPIs met in shadow runs; bias checks pass.

---

## 14. Backup, Restore & Disaster Recovery

**Goal:** survive the worst day.

* **Backups:** Postgres PITR tested; object store versioning; Kafka retention verified.
* **Restore drills:** full environment rebuild from IaC; RPO ≤ 15 min for critical data.
* **Key loss scenarios:** rotate and re-establish secrets without downtime.

**Pass gate:** restore to last backup within RTO; data integrity verified.

---

## 15. Release Engineering, Flags & Rollback

**Goal:** safe delivery.

* **Feature flags:** per-connector flag; dark launch → canary → 50% → 100%.
* **Blue/Green & canary:** automated health checks; automatic rollback on SLI breach.
* **DB migrations:** online, backward compatible; expand/contract pattern.
* **Version pinning:** connectors versioned; consumer-driven contract tests block breaking changes.

**Pass gate:** zero-downtime releases; instant rollback validated.

---

## 16. Documentation & Runbooks

**Goal:** operability under stress.

* **Runbook test:** new on-call uses docs to resolve seeded incidents.
* **Playbooks:** connector outage, webhook flood, reconciliation drift, Stripe webhook failure, Kafka lag.
* **SLO policy:** alert thresholds & escalation tested (paging dry run).

**Pass gate:** time-to-mitigate within target; runbook gaps closed.

---

## Tooling & Automation Map

* **Unit/Integration:** Jest, PyTest, Testcontainers, Pact, WireMock.
* **Property-based/Fuzz:** Hypothesis (Python), fast-check (TypeScript), Zest/OttFuzz for REST.
* **E2E/UI:** Playwright, axe-core, Lighthouse CI.
* **Performance/Soak:** k6, Locust; Prometheus metrics exported.
* **Chaos:** Toxiproxy, Chaos Mesh, Litmus.
* **Security:** ZAP/Burp (DAST), Trivy/Dockle (container), Snyk/Semgrep (SCA/SAST), Gitleaks.
* **Data Quality:** Great Expectations/Deequ; dbt tests for transforms.
* **ML:** EvidentlyAI, Alibi Detect.
* **IaC & Policy:** Terraform + Terratest; OPA/Conftest.

---

## Codex-Executable Test Jobs (Examples)

```json
{
  "jobs": [
    {
      "name": "unit-sdk",
      "cmd": "pnpm test --filter @prep/sdk --coverage",
      "pass_if": "coverage >= 0.85 && mutants_killed >= 0.70"
    },
    {
      "name": "contract-square",
      "cmd": "pact-broker verify --provider square --publish",
      "on_fail": "block_merge"
    },
    {
      "name": "e2e-delivery-only",
      "cmd": "playwright test e2e/delivery_only.spec.ts",
      "env": {"SANDBOX": "true"}
    },
    {
      "name": "perf-gateway",
      "cmd": "k6 run tests/perf/gateway-smoke.js",
      "pass_if": "p95_latency_ms < 300 && error_rate < 0.005"
    },
    {
      "name": "chaos-webhooks",
      "cmd": "toxiproxyctl set connector --toxic latency --latency 800 --jitter 200 && pnpm test e2e/webhook_resilience.spec.ts"
    },
    {
      "name": "zap-dast",
      "cmd": "zap-baseline.py -t https://staging.prep.app -r zap.html",
      "pass_if": "no_critical_findings"
    },
    {
      "name": "ge-data-quality",
      "cmd": "great_expectations checkpoint run pos_reconciliation.yml",
      "pass_if": "critical_expectations_passed"
    }
  ]
}
```

---

## Representative Test Cases

**Property-based idempotency test (Python):**

```python
from hypothesis import given, strategies as st

@given(order_id=st.uuids(), dup=st.integers(min_value=1, max_value=5))
def test_webhook_idempotency(order_id, dup):
    for _ in range(dup):
        resp = client.post("/webhooks/doorDash", json=payload(order_id))
        assert resp.status_code in (200, 204)
    # verify single state transition & one ledger entry
    assert db.count("deliveries", order_id=order_id) == 1
```

**Playwright delivery-only flow (happy path + offline resume):**

```ts
test('delivery-only booking + offline resume', async ({ page }) => {
  await page.goto('/login'); await loginAsRenter(page);
  await page.goto('/kitchens?deliveryOnly=true');
  await page.getByText('Midtown Commissary').click();
  await page.getByRole('button', { name: 'Book' }).click();
  await page.context().setOffline(true);
  await page.reload(); // PWA cache
  await page.context().setOffline(false);
  await page.getByRole('button', { name: 'Confirm' }).click();
  await expect(page.getByText('Booking Confirmed')).toBeVisible();
});
```

**k6 gateway smoke:**

```js
import http from 'k6/http';
import { check, sleep } from 'k6';
export const options = { vus: 50, duration: '5m', thresholds: { http_req_duration: ['p(95)<300'] }};
export default function () {
  const res = http.get(`${__ENV.API}/health`);
  check(res, { 'status 200': (r) => r.status === 200 });
  sleep(0.5);
}
```

---

## Exit Criteria & Promotion Rules

* **Canary readiness:** all critical E2E flows green for three consecutive runs; performance p95 < 300 ms; error rate < 0.5%.
* **Security gate:** zero critical/high unwaived findings; secrets scan clean.
* **Compliance gate:** delivery-only manifests generated & validated against sample city checklists; insurance certificate attached.
* **DR drill:** restore rehearsal completed within the last 30 days.
* **Observability:** dashboards present with SLIs and alert routes tested.

---

## Implementation Order

1. Wire **test scaffolding** (runners, reporters, coverage, thresholds).
2. Implement **unit + mutation** tests on core libraries.
3. Add **contract + integration** coverage (WireMock/Pact) per connector.
4. Layer **E2E** happy → edge → chaos → performance suites.
5. Add **security, privacy, data quality** gates.
6. Finalize **DR, runbooks, SLOs, and release** validation.

---

*Prepared for autonomous execution by Codex and CI pipelines.*
