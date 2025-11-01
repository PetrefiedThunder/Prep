# Prep Platform Demo Script

> **Format:** Product overview and technical demonstration.

---

## 0:00 – 0:30 — Introduction
- "Prep is a regulatory compliance platform for commercial food facilities. Commercial kitchens operate under multiple overlapping regulatory jurisdictions."
- "Missing compliance requirements can result in operational shutdowns and financial penalties."
- "Prep automates compliance monitoring and verification across all regulatory layers."

## 0:30 – 1:15 — Problem Overview
- "Kitchen operators must comply with federal FSMA rules, state regulations, city ordinances, and private certification bodies. These systems operate independently."
- "Geographic expansion requires understanding new jurisdictional requirements and local regulations."
- "Manual compliance tracking uses spreadsheets, physical documentation, and reactive monitoring."
- Key takeaway: Traditional compliance management is fragmented and error-prone.

## 1:15 – 2:00 — Solution Architecture
- "Prep provides automated regulatory compliance orchestration."
- Architecture: Federal → State → City → Facility validation chain.
- "System ingests federal accreditation data, normalizes state regulations, and integrates local ordinances."
- "Operators specify their operations, and Prep identifies required permits, inspections, certifications, and renewal schedules."

## 2:00 – 2:45 — Implementation Status
- "Platform currently tracks compliance for commercial facilities across multiple jurisdictions."
- "Active development includes expanded state coverage and enterprise integrations."
- "Subscription model with tiered pricing based on facility count and geographic coverage."
- "Low churn due to critical nature of compliance monitoring for operational continuity."

## 2:45 – 3:00 — Platform Vision
- "Roadmap includes expanded jurisdictional coverage and enterprise API integrations."
- "Vision: Prep as the regulatory compliance infrastructure for multi-jurisdictional food operations."
- End with product architecture overview.

---

## Demo Walkthrough (2 Minutes)

### Step 1 — Dashboard Overview (0:00 – 0:30)
- Show `apps/web/src/pages/Dashboard.tsx` compliance heatmap.
- Highlight upcoming inspections and expiring permits.

### Step 2 — California State Layer Preview (0:30 – 1:00)
- Switch to `apps/web/src/pages/ComplianceMap.tsx` with state toggle.
- Filter for California to show statewide requirements alongside Los Angeles city overlays.

### Step 3 — Facility Drill-Down (1:00 – 1:30)
- Open `apps/web/src/pages/facilities/[id].tsx`.
- Demonstrate automated checklist, highlighting CalCode references and city cross-links.

### Step 4 — Instant Audit Report (1:30 – 2:00)
- Trigger export via `prep/reporting/audit_packet.py`.
- Show PDF summary and JSON payload ready for inspectors.

---

## Closing Summary
"Prep automates compliance monitoring, enabling operators to focus on core business operations rather than regulatory documentation management."

