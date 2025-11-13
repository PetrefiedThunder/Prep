# Service Level Objectives (SLOs)

## Purpose

This document defines the Service Level Objectives (SLOs) for the Prep platform. SLOs are measurable targets for service reliability, latency, and availability that guide engineering priorities and incident response.

---

## SLO Philosophy

> **"Perfect reliability is impossible and unnecessary. We target 99.9% (three nines) for critical user journeys."**

### Error Budget

- **99.9% availability** = 43 minutes of downtime per month
- **99.5% availability** = 3.6 hours of downtime per month

When error budget is exhausted, **all engineering effort shifts to reliability** until the budget recovers.

---

## Critical User Journeys

These are the user flows that MUST be highly available:

1. **Compliance Check** (vendor onboarding)
2. **Booking Creation** (revenue-generating)
3. **Payment Processing** (revenue-critical)
4. **Permit Lookup** (compliance-critical)
5. **Dashboard Load** (daily user workflow)

---

## SLOs by Service

### 1. Compliance Service

**Purpose**: Evaluate regulatory compliance for properties.

| Metric | SLO Target | Measurement Window | Error Budget |
|--------|-----------|-------------------|--------------|
| **Availability** | 99.9% | 30 days | 43 min/month |
| **Latency (P95)** | < 2000ms | 1 day | 5% > 2000ms |
| **Latency (P99)** | < 5000ms | 1 day | 1% > 5000ms |
| **Error Rate** | < 0.5% | 1 hour | 0.5% errors |
| **Correctness** | 99.95% | 30 days | 0.05% wrong results |

**Rationale**:
- Compliance checks are asynchronous (not user-blocking)
- 2-5 second latency is acceptable for complex rule evaluation
- Correctness is paramount (false positives harm trust)

**Alerting Thresholds**:
- Page on-call: Error rate > 1% for 5 minutes
- Warn team: P95 latency > 3000ms for 10 minutes
- Ticket: Availability < 99.5% over 7 days

---

### 2. Booking Service

**Purpose**: Handle booking creation and management.

| Metric | SLO Target | Measurement Window | Error Budget |
|--------|-----------|-------------------|--------------|
| **Availability** | 99.95% | 30 days | 22 min/month |
| **Latency (P95)** | < 500ms | 1 day | 5% > 500ms |
| **Latency (P99)** | < 1000ms | 1 day | 1% > 1000ms |
| **Error Rate** | < 0.1% | 1 hour | 0.1% errors |

**Rationale**:
- Bookings are revenue-critical (higher SLO than compliance)
- Users expect fast responses (< 500ms feels instant)
- Booking failures directly impact revenue

**Alerting Thresholds**:
- Page on-call: Error rate > 0.5% for 5 minutes
- Page on-call: Availability < 99.9% for 10 minutes
- Warn team: P95 latency > 800ms for 10 minutes

---

### 3. Payment Service

**Purpose**: Process payments via Stripe.

| Metric | SLO Target | Measurement Window | Error Budget |
|--------|-----------|-------------------|--------------|
| **Availability** | 99.99% | 30 days | 4 min/month |
| **Latency (P95)** | < 1000ms | 1 day | 5% > 1000ms |
| **Latency (P99)** | < 3000ms | 1 day | 1% > 3000ms |
| **Error Rate** | < 0.05% | 1 hour | 0.05% errors |
| **Payment Success Rate** | > 99.5% | 1 day | 0.5% failures |

**Rationale**:
- Payment failures = direct revenue loss
- Highest availability target (four nines)
- Dependency on Stripe (factor into error budget)

**Alerting Thresholds**:
- Page on-call: Error rate > 0.1% for 5 minutes
- Page on-call: Availability < 99.95% for 5 minutes
- Page on-call: Payment success rate < 99% for 10 minutes

---

### 4. API Gateway

**Purpose**: Route requests to backend services.

| Metric | SLO Target | Measurement Window | Error Budget |
|--------|-----------|-------------------|--------------|
| **Availability** | 99.99% | 30 days | 4 min/month |
| **Latency (P95)** | < 100ms | 1 day | 5% > 100ms |
| **Latency (P99)** | < 200ms | 1 day | 1% > 200ms |
| **Error Rate** | < 0.01% | 1 hour | 0.01% errors |

**Rationale**:
- Gateway is a single point of failure
- Must be extremely fast and reliable
- Errors here affect all downstream services

**Alerting Thresholds**:
- Page on-call: Error rate > 0.1% for 5 minutes
- Page on-call: Availability < 99.95% for 5 minutes
- Warn team: P95 latency > 150ms for 10 minutes

---

### 5. Dashboard / Web UI

**Purpose**: User-facing dashboard for operators.

| Metric | SLO Target | Measurement Window | Error Budget |
|--------|-----------|-------------------|--------------|
| **Availability** | 99.9% | 30 days | 43 min/month |
| **Time to Interactive** | < 2000ms | 1 day | 5% > 2000ms |
| **Largest Contentful Paint** | < 2500ms | 1 day | 25% > 2500ms |
| **Cumulative Layout Shift** | < 0.1 | 1 day | 25% > 0.1 |

**Rationale**:
- Dashboard is async (not revenue-blocking)
- User experience matters but not time-critical
- Web vitals guide user-perceived performance

**Alerting Thresholds**:
- Warn team: Availability < 99.5% for 10 minutes
- Warn team: Time to Interactive > 3000ms for 20 minutes

---

### 6. Regulatory Data Pipeline

**Purpose**: Ingest and process regulatory updates.

| Metric | SLO Target | Measurement Window | Error Budget |
|--------|-----------|-------------------|--------------|
| **Freshness** | < 24 hours | 7 days | 5% stale |
| **Completeness** | > 99.5% | 7 days | 0.5% missing |
| **Error Rate** | < 1% | 1 day | 1% errors |

**Rationale**:
- Regulatory data changes slowly (24h freshness OK)
- Missing data is worse than stale data
- Non-real-time (batch processing)

**Alerting Thresholds**:
- Ticket: Freshness > 48 hours
- Warn team: Completeness < 95%

---

## Measurement & Monitoring

### Metrics Collection

**Prometheus** collects metrics from all services:

```yaml
# Example Prometheus metrics
http_requests_total{service="booking",method="POST",status="200"} 1523
http_request_duration_seconds_bucket{service="booking",le="0.5"} 1450
http_request_duration_seconds_bucket{service="booking",le="1.0"} 1520
compliance_check_duration_seconds_sum{jurisdiction="SF"} 234.5
compliance_check_duration_seconds_count{jurisdiction="SF"} 123
```

### Dashboards

**Grafana** dashboards for each service:

1. **Golden Signals Dashboard**: Latency, traffic, errors, saturation
2. **Service Health Dashboard**: Availability, error rates, SLO burn rate
3. **Business Metrics Dashboard**: Bookings/day, revenue, compliance checks
4. **Dependency Dashboard**: Stripe API health, database latency

### Alerting Rules

```yaml
# Prometheus alerting rules
groups:
  - name: slo_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
            /
            sum(rate(http_requests_total[5m])) by (service)
          ) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on {{ $labels.service }}"
          description: "Error rate is {{ $value | humanizePercentage }}"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
          ) > 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High P95 latency on {{ $labels.service }}"
          description: "P95 latency is {{ $value }}s"

      - alert: PaymentFailures
        expr: |
          (
            sum(rate(payment_attempts_total{status="failed"}[5m]))
            /
            sum(rate(payment_attempts_total[5m]))
          ) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High payment failure rate"
          description: "Payment failure rate is {{ $value | humanizePercentage }}"
```

---

## SLO Burn Rate Alerts

**Burn rate** = how fast we're consuming error budget.

| Burn Rate | Error Budget Consumed | Time to Exhaustion | Response |
|-----------|----------------------|-------------------|----------|
| **1x** | 1% per hour | 4 days | Normal operations |
| **2x** | 2% per hour | 2 days | Monitor closely |
| **10x** | 10% per hour | 10 hours | Page on-call |
| **100x** | 100% per hour | 1 hour | Critical incident |

**Alert Configuration**:

```yaml
- alert: FastBurnRate
  expr: |
    (
      1 - (
        sum(rate(http_requests_total{status=~"2.."}[1h])) by (service)
        /
        sum(rate(http_requests_total[1h])) by (service)
      )
    ) > 0.01  # Burning > 10x normal rate
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Fast SLO burn rate on {{ $labels.service }}"
    description: "Error budget will be exhausted in < 10 hours"
```

---

## Incident Response

### Severity Levels

| Severity | Definition | Response Time | Example |
|----------|-----------|--------------|---------|
| **P0** | Complete outage | Immediate | API down, no bookings possible |
| **P1** | Critical degradation | < 15 minutes | Payment success rate < 95% |
| **P2** | Significant degradation | < 1 hour | P95 latency > 2x SLO |
| **P3** | Minor degradation | < 4 hours | Dashboard slow but functional |
| **P4** | Potential issue | Next business day | SLO at 99.85% (near budget) |

### Incident Workflow

1. **Detect**: Alert fires → PagerDuty pages on-call engineer
2. **Acknowledge**: On-call acks alert within 5 minutes
3. **Investigate**: Gather data, check dashboards, logs, traces
4. **Mitigate**: Apply temporary fix to restore service
5. **Resolve**: Apply permanent fix
6. **Post-Mortem**: Blameless write-up within 48 hours

---

## Error Budget Policy

### When Error Budget is Healthy (> 50%)

- Ship new features
- Experiment with new tech
- Refactor aggressively
- Deploy multiple times per day

### When Error Budget is Low (< 25%)

- **Freeze non-critical deployments**
- Focus on reliability improvements
- Pay down technical debt
- Increase test coverage
- Review and improve monitoring

### When Error Budget is Exhausted (< 0%)

- **Complete feature freeze**
- All hands on reliability
- Root cause analysis for all incidents
- Fix underlying issues, not symptoms
- Deploy only critical bug fixes

---

## SLO Review Process

### Weekly SLO Review

Every Monday, engineering reviews:

1. Error budget remaining for each service
2. Incidents from past week
3. Trends in latency, errors, availability
4. Action items to improve reliability

### Quarterly SLO Tuning

Every quarter, product + engineering review:

1. Are SLOs too strict? (constantly exhausting budget)
2. Are SLOs too loose? (always exceeding targets)
3. Do SLOs align with user expectations?
4. Should we add/remove SLOs?

---

## Instrumentation Guide

### Adding Metrics to Code

**Python (FastAPI)**:

```python
from prometheus_client import Counter, Histogram, Gauge
from prep.observability import metrics

# Define metrics
compliance_checks_total = Counter(
    "compliance_checks_total",
    "Total compliance checks performed",
    ["jurisdiction", "result"],
)

compliance_check_duration = Histogram(
    "compliance_check_duration_seconds",
    "Time to perform compliance check",
    ["jurisdiction"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

@router.post("/api/v1/compliance/check")
async def check_compliance(request: ComplianceRequest):
    with compliance_check_duration.labels(jurisdiction=request.jurisdiction).time():
        result = await compliance_engine.evaluate(request)

    compliance_checks_total.labels(
        jurisdiction=request.jurisdiction,
        result="compliant" if result.compliant else "non_compliant",
    ).inc()

    return result
```

**TypeScript (NestJS)**:

```typescript
import { Counter, Histogram } from 'prom-client';

const bookingAttempts = new Counter({
  name: 'booking_attempts_total',
  help: 'Total booking attempts',
  labelNames: ['status'],
});

const bookingDuration = new Histogram({
  name: 'booking_duration_seconds',
  help: 'Time to create booking',
  buckets: [0.1, 0.3, 0.5, 1.0, 2.0],
});

async createBooking(dto: CreateBookingDto) {
  const timer = bookingDuration.startTimer();

  try {
    const booking = await this.bookingService.create(dto);
    bookingAttempts.inc({ status: 'success' });
    return booking;
  } catch (error) {
    bookingAttempts.inc({ status: 'failure' });
    throw error;
  } finally {
    timer();
  }
}
```

---

## Document Metadata

- **Version**: 1.0
- **Last Updated**: 2025-11-13
- **Owner**: Platform Engineering + SRE
- **Review Cycle**: Monthly for metrics, Quarterly for SLO targets
- **Approval Required**: VP Engineering for SLO changes

---

## Related Documents

- [Architecture Overview](./architecture.md)
- [Incident Response Playbook](../RUNBOOK.md)
- [Monitoring Setup Guide](./observability_setup.md)

---

## Appendix: SLO Calculation Examples

### Availability SLO

```
Availability = (Successful Requests / Total Requests) × 100%

Example:
- Total requests in 30 days: 10,000,000
- Failed requests (5xx errors): 10,000
- Availability = (9,990,000 / 10,000,000) × 100% = 99.9% ✓ (meets SLO)
```

### Latency SLO

```
P95 Latency = 95th percentile of response times

Example:
- 95% of requests complete in < 500ms
- 5% of requests take 500-2000ms
- P95 latency = 500ms ✓ (meets SLO)
```

### Error Budget Calculation

```
Error Budget = (1 - SLO) × Total Requests

Example:
- SLO = 99.9%
- Total requests in 30 days = 10,000,000
- Error budget = (1 - 0.999) × 10,000,000 = 10,000 failed requests allowed
- Actual failures = 8,000
- Error budget remaining = 2,000 requests (20% remaining) ✓
```
