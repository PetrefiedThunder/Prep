# RegEngine - Regulatory Compliance Engine

## Purpose

RegEngine is the compliance kernel that evaluates properties, bookings, and operations against multi-jurisdictional regulatory rules. It transforms complex regulatory requirements into executable, testable, and auditable rule configurations.

---

## Architecture

```
regengine/
├── cities/                          # Jurisdiction-specific rules
│   ├── san_francisco/
│   │   ├── config.yaml             # SF regulatory config
│   │   ├── rules.yaml              # SF compliance rules (NEW)
│   │   └── fixtures/
│   │       ├── fee_schedule.yaml
│   │       └── config.yaml
│   ├── los_angeles/
│   │   ├── config.yaml
│   │   └── rules.yaml
│   ├── compliance_kernel.py        # Core evaluation engine
│   ├── fee_engine.py               # Fee calculation
│   └── calendar_conflict_engine.py # Booking conflicts
├── tests/
│   ├── test_harness.py             # Golden file testing
│   └── test_scenarios.py           # Scenario tests (NEW)
└── visualize.py                    # DAG visualization (NEW)
```

---

## Core Concepts

### 1. **Compliance Rules**

Rules are defined in YAML with:
- **Rule ID**: Unique identifier (e.g., `SF-BRC-001`)
- **Name**: Human-readable name
- **Description**: What the rule checks
- **Severity**: `blocking`, `warning`, `info`
- **Conditions**: When the rule applies
- **Remedy**: How to fix violations
- **Citation**: Legal reference

### 2. **Rule Evaluation**

The compliance kernel evaluates rules in dependency order:

```
1. Business Registration → Must pass before other checks
2. Zoning → Must be in allowed district
3. Permits → Required permits must be valid
4. Insurance → Coverage minimums met
5. Operational Limits → Booking fits constraints
```

### 3. **DAG (Directed Acyclic Graph)**

Rules form a dependency graph:

```
Business Registration
    ├─→ Health Permit
    │   └─→ Fire Inspection
    └─→ TOB Registration
        └─→ Tax Compliance

Zoning Check (independent)
Insurance Check (independent)
```

---

## Rule Definition Format

### Example: San Francisco Business Registration

```yaml
rules:
  - id: SF-BRC-001
    name: "Business Registration Certificate Required"
    description: "All STR operators must have active Business Registration Certificate"
    severity: blocking
    category: business_license

    conditions:
      property_type:
        - entire_home
        - private_room
        - shared_room

    checks:
      - field: vendor.business_registration.status
        operator: equals
        value: active
      - field: vendor.business_registration.expiration_date
        operator: greater_than
        value: today

    violation:
      message: "Business Registration Certificate is required and must be active"
      remedy: "Apply at https://businessportal.sfgov.org"
      estimated_time: "2-3 weeks"
      cost: "$91"

    citation: "SF Business and Tax Regulations Code Article 12-A"
    url: "https://sf.gov/information/register-your-business"

    dependencies: []  # No prerequisites
```

### Example: Fire Inspection (with dependency)

```yaml
  - id: SF-FIRE-001
    name: "Fire Safety Inspection Required"
    description: "Properties must pass annual fire safety inspection"
    severity: blocking
    category: fire_safety

    conditions:
      property_type:
        - entire_home
      has_cooking: true

    checks:
      - field: facility.inspections.fire.status
        operator: equals
        value: passed
      - field: facility.inspections.fire.date
        operator: within_days
        value: 365

    violation:
      message: "Fire safety inspection required (annual)"
      remedy: "Schedule inspection with SFFD"
      estimated_time: "2-4 weeks"
      cost: "$150"

    citation: "SF Fire Code Section 901"

    dependencies:
      - SF-BRC-001  # Must have business registration first
```

---

## Usage

### Python API

```python
from regengine.cities import MunicipalComplianceKernel

# Initialize kernel for SF
kernel = MunicipalComplianceKernel("san_francisco")

# Evaluate a booking
evaluation = kernel.evaluate_booking(
    facility=facility_data,
    booking=booking_data,
    vendor=vendor_data
)

# Check result
if evaluation.result == ComplianceResult.ALLOW:
    print("✓ Booking approved")
elif evaluation.result == ComplianceResult.CONDITIONS:
    print("⚠ Booking approved with conditions:")
    for condition in evaluation.conditions:
        print(f"  - {condition}")
else:  # DENY
    print("✗ Booking denied:")
    for violation in evaluation.violations:
        print(f"  - {violation.message}")
        print(f"    Remedy: {violation.remedy}")
```

### CLI

```bash
# Check compliance for a facility
prepctl compliance:check --facility-id facility-123 --jurisdiction SF

# Validate rule definitions
prepctl regengine:validate --jurisdiction SF

# Generate rule DAG
prepctl regengine:visualize --jurisdiction SF --output dag.png

# Run golden file tests
prepctl regengine:test --jurisdiction SF
```

---

## Rule Categories

| Category | Description | Typical Severity |
|----------|-------------|------------------|
| `business_license` | Business registration requirements | Blocking |
| `zoning` | Land use and zoning compliance | Blocking |
| `permits` | Required permits and licenses | Blocking |
| `health` | Health department requirements | Blocking |
| `fire_safety` | Fire code compliance | Blocking |
| `insurance` | Insurance coverage minimums | Blocking |
| `tax` | Tax registration and payment | Blocking |
| `operational` | Booking limits, noise, etc. | Warning |
| `reporting` | Reporting and disclosure | Info |

---

## Severity Levels

### Blocking
- Prevents booking from being approved
- Must be resolved before proceeding
- Examples: Missing permit, expired license

### Warning
- Booking can proceed with caution
- Should be addressed soon
- Examples: Approaching inspection due date, high complaint count

### Info
- Informational only
- No blocking
- Examples: Reminder to update insurance policy

---

## Rule Evaluation Algorithm

```python
def evaluate(facility, booking, vendor):
    evaluation = ComplianceEvaluation(jurisdiction_id)

    # 1. Load all rules for jurisdiction
    rules = load_rules(jurisdiction_id)

    # 2. Sort rules by dependency order (topological sort)
    sorted_rules = topological_sort(rules)

    # 3. Evaluate each rule
    for rule in sorted_rules:
        # Check if rule applies to this booking
        if not rule_applies(rule, facility, booking):
            continue

        # Check if dependencies are satisfied
        if not dependencies_satisfied(rule, evaluation):
            evaluation.add_violation(
                ComplianceViolation(
                    rule_id=rule.id,
                    severity="high",
                    message=f"Prerequisite {rule.dependency} not met"
                )
            )
            continue

        # Evaluate rule checks
        for check in rule.checks:
            if not evaluate_check(check, facility, booking, vendor):
                evaluation.add_violation(
                    ComplianceViolation(
                        rule_id=rule.id,
                        severity=rule.severity,
                        message=rule.violation.message,
                        remedy=rule.violation.remedy,
                        citation=rule.citation
                    )
                )
                break

    return evaluation
```

---

## Golden File Testing

RegEngine uses golden file testing to ensure rule stability:

```yaml
# tests/golden/sf_compliant.yaml
description: "Fully compliant SF property"
jurisdiction: san_francisco

facility:
  property_type: entire_home
  zoning_district: NC-3
  permits:
    - type: business_registration
      status: active
      expiration_date: 2026-01-01
    - type: health_permit
      status: valid
      expiration_date: 2025-12-31
    - type: tob_registration
      status: active

booking:
  check_in: 2025-12-01
  check_out: 2025-12-03
  guest_count: 2

vendor:
  business_registration:
    status: active
    expiration_date: 2026-01-01

expected_result: ALLOW
expected_violations: []
expected_warnings: []
```

Run tests:
```bash
pytest regengine/tests/test_harness.py
```

---

## DAG Visualization

Generate visual dependency graphs:

```bash
# Generate DAG for San Francisco rules
python regengine/visualize.py --jurisdiction san_francisco --output sf_dag.png
```

Output:
```
                    [SF-BRC-001]
                 Business Registration
                  /                  \
                 /                    \
        [SF-HEALTH-001]         [SF-TOB-001]
        Health Permit           TOB Registration
              |                        |
              |                        |
        [SF-FIRE-001]            [SF-TAX-001]
      Fire Inspection           Tax Compliance


         [SF-ZONING-001]       [SF-INSURANCE-001]
         Zoning Check          Insurance Check
        (independent)           (independent)
```

---

## Adding a New Jurisdiction

### Step 1: Create jurisdiction directory

```bash
mkdir -p regengine/cities/seattle
```

### Step 2: Create config.yaml

```yaml
id: seattle
display: "Seattle"
state: WA
permit_kinds:
  - str_license
  - business_license
# ... (copy from san_francisco and customize)
```

### Step 3: Create rules.yaml

```yaml
rules:
  - id: SEA-BL-001
    name: "Business License Required"
    # ... rule definition
```

### Step 4: Add golden test files

```bash
mkdir -p regengine/tests/golden/seattle
# Add compliant and non-compliant test cases
```

### Step 5: Run tests

```bash
prepctl regengine:test --jurisdiction seattle
```

---

## Performance Characteristics

| Operation | Latency (P95) | Notes |
|-----------|---------------|-------|
| Rule evaluation | < 50ms | For ~50 rules |
| Rule loading | < 10ms | Cached after first load |
| DAG generation | < 200ms | On-demand only |
| Golden tests | ~2s | Full test suite |

---

## Caching Strategy

```python
class ComplianceKernel:
    def __init__(self):
        self._rule_cache = {}  # Jurisdiction → Rules
        self._dag_cache = {}   # Jurisdiction → DAG

    def load_rules(self, jurisdiction):
        if jurisdiction not in self._rule_cache:
            self._rule_cache[jurisdiction] = _load_from_yaml(jurisdiction)
        return self._rule_cache[jurisdiction]
```

Cache invalidation:
- Rules cached until process restart
- Development: Disable cache with `REGENGINE_CACHE=0`
- Production: Cache persists for process lifetime

---

## Monitoring & Metrics

Key metrics to track:

```python
# Prometheus metrics
regengine_evaluations_total{jurisdiction, result}
regengine_evaluation_duration_seconds{jurisdiction}
regengine_rule_violations_total{jurisdiction, rule_id}
regengine_cache_hits_total{jurisdiction}
```

---

## Compliance Reporting

Export compliance reports:

```bash
# Export all evaluations for a facility
prepctl compliance:export \
  --facility-id facility-123 \
  --format pdf \
  --output compliance-report.pdf
```

Report includes:
- All evaluations (pass/fail)
- Violation history
- Resolution timeline
- Citation references
- Audit trail

---

## Document Metadata

- **Version**: 1.0
- **Last Updated**: 2025-11-13
- **Owner**: Compliance Engineering Team
- **Review Cycle**: After each jurisdiction addition

---

## Related Documents

- [Architecture Overview](../docs/architecture.md)
- [Compliance Engine](../docs/compliance_engine.md)
- [Golden Path Demo](../docs/GOLDEN_PATH_DEMO.md)
