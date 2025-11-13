# Product Spine - Prep Platform

## Purpose

This document defines the **core product narrative** for the Prep platform - the essential features and capabilities that define our product identity and competitive differentiation.

## Core Value Proposition

**Prep turns compliance from a blocker into a competitive advantage for short-term rental operators.**

We automate regulatory compliance across multiple jurisdictions, eliminating manual paperwork, reducing risk, and enabling operators to scale confidently.

---

## The Product Spine (Core Features)

These are the **non-negotiable** features that define the Prep platform. Everything else is an enhancement.

### 1. **Multi-Jurisdiction Compliance Engine**

**What**: Automated compliance checking against city, county, state, and federal regulations for short-term rentals.

**Why it matters**: Manual compliance is error-prone, time-consuming, and doesn't scale. We automate it.

**Key capabilities**:
- Rule-based evaluation engine (RegEngine)
- Support for LA County, San Francisco, Seattle, Portland (expanding)
- Real-time compliance status per property
- Automated document requirements tracking

**User outcome**: "I know exactly what permits and documents I need for each property, automatically."

---

### 2. **Intelligent Document Management**

**What**: Centralized document vault with automated expiration tracking, renewal reminders, and compliance mapping.

**Why it matters**: Regulatory documents expire, requirements change. We prevent compliance lapses.

**Key capabilities**:
- Secure document storage (encrypted at rest)
- Expiration tracking and proactive alerts
- Document-to-requirement mapping
- Audit trail for all document changes

**User outcome**: "I never miss a permit renewal or inspection deadline."

---

### 3. **Automated Fee Calculation & Payment Processing**

**What**: Jurisdiction-specific fee calculation engine with automated payment processing via Stripe Connect.

**Why it matters**: Fee schedules are complex, change frequently, and vary by jurisdiction. We get it right.

**Key capabilities**:
- Dynamic fee calculation based on property attributes
- Stripe Connect for split payments (platform + jurisdictions)
- Fee schedule versioning and change tracking
- Transparent fee breakdowns for operators

**User outcome**: "I pay the exact right amount to the right agencies, automatically."

---

### 4. **Real-Time Regulatory Monitoring**

**What**: Continuous monitoring of regulatory changes across supported jurisdictions with impact analysis.

**Why it matters**: Regulations change constantly. Operators can't track every city council meeting.

**Key capabilities**:
- Automated regulatory change detection
- Impact analysis: "These 5 properties are affected"
- Proactive notifications to affected operators
- Grace period tracking for new requirements

**User outcome**: "I'm notified immediately when regulations change that affect my properties."

---

### 5. **Compliance Dashboard & Reporting**

**What**: Real-time compliance status across all properties with drill-down reporting and export capabilities.

**Why it matters**: Operators need visibility. Auditors need proof. Investors need confidence.

**Key capabilities**:
- Portfolio-level compliance overview
- Property-level compliance details
- Compliance history and audit logs
- Export to PDF/CSV for audits and due diligence

**User outcome**: "I can prove compliance to auditors, investors, or agencies in 30 seconds."

---

## What We Are NOT (Intentional Boundaries)

These are explicit **anti-features** - things we intentionally don't do to maintain focus:

- ❌ **Property listing management** (use Airbnb, VRBO, etc.)
- ❌ **Booking management** (use your existing PMS)
- ❌ **Guest communication** (use your existing tools)
- ❌ **Pricing optimization** (use PriceLabs, Wheelhouse, etc.)
- ❌ **Channel management** (use Hostaway, Guesty, etc.)

**Why**: We integrate with best-in-class tools. We focus on compliance, not reinventing the wheel.

---

## Integration Philosophy

**Prep is a compliance layer that plugs into your existing stack.**

### Core Integrations (Required for Product Spine):
1. **Property Management Systems**: Hostaway, Guesty, Lodgify
2. **Payment Processors**: Stripe Connect
3. **Document Storage**: AWS S3, MinIO
4. **Accounting Systems**: QuickBooks, Xero (for audit trail)

### Future Integrations (Enhancement Layer):
- Government portals (LA Housing, SF Planning)
- Insurance providers (compliance verification)
- Background check services (for operator verification)

---

## Success Metrics

How we measure whether the Product Spine is working:

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| **Time to Compliance** | < 24 hours from property onboarding | Speed is competitive advantage |
| **Compliance Accuracy** | 99.5%+ (measured by audit success rate) | Trust is everything |
| **Regulatory Change Detection** | < 48 hours from regulation publication | Proactive > reactive |
| **Document Expiration Prevention** | 0 missed renewals for active users | Core promise |
| **Fee Calculation Accuracy** | 100% (zero disputes with agencies) | Financial integrity |

---

## Product Principles

These principles guide all product decisions:

### 1. **Compliance-First, Always**
If a feature doesn't improve compliance outcomes, we deprioritize it.

### 2. **Automate the Tedious**
Manual processes don't scale. If a human can be removed from the loop, do it.

### 3. **Trust Through Transparency**
Every compliance decision is explainable, auditable, and backed by regulatory citation.

### 4. **Integrate, Don't Replicate**
We build compliance tools, not yet another PMS. Integrate with existing workflows.

### 5. **Progressive Disclosure**
Simple by default, powerful when needed. Don't overwhelm users with complexity upfront.

---

## Roadmap Alignment

All features must align with the Product Spine. Use this decision tree:

```
Does this feature...
├─ Improve compliance accuracy? → Yes → High Priority
├─ Reduce compliance time? → Yes → High Priority
├─ Increase trust/auditability? → Yes → Medium Priority
├─ Enable new jurisdictions? → Yes → Strategic Priority
└─ None of the above? → Deprioritize or say no
```

---

## For Engineering Teams

When building features, ask:

1. **Does this serve the Product Spine?** If not, challenge the requirement.
2. **Is this the minimum viable implementation?** Ship fast, iterate.
3. **Is this auditable?** Every compliance decision needs a paper trail.
4. **Does this scale to 100 jurisdictions?** Build for multi-jurisdiction from day one.

---

## Document Metadata

- **Version**: 1.0
- **Last Updated**: 2025-11-13
- **Owner**: Product Team
- **Stakeholders**: Engineering, Compliance, GTM
- **Review Cycle**: Quarterly (or when strategic direction changes)

---

## Related Documents

- [Architecture Overview](./architecture.md)
- [API Versioning Policy](./API_VERSIONING_POLICY.md)
- [Compliance Engine](./compliance_engine.md)
- [SLO Definitions](./SLO.md)
