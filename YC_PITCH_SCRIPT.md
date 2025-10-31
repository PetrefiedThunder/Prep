# Prep YC Demo Day Script

> **Format:** 3-minute founder pitch followed by 2-minute product demo walkthrough.

---

## 0:00 – 0:30 — Cold Open
- "I'm Alex, co-founder of Prep. Commercial kitchens live under 4 overlapping regulators. Missing a single permit can shut them down overnight." 
- Flash slide: `41%` of independent kitchens fail a compliance check in California.
- "Prep keeps every kitchen inspection-ready, automatically."

## 0:30 – 1:15 — Problem & Insight
- "Kitchen operators juggle federal FSMA rules, state code, city ordinances, and private certification bodies. None of those systems talk to each other."
- "When a kitchen expands to San Francisco, they have to re-learn 87 pages of local code."
- "We saw kitchens losing tens of thousands in wasted inventory because their certifier lapsed." 
- Key takeaway slide: Manual compliance = spreadsheets + binders + frantic calls.

## 1:15 – 2:00 — Solution & Product
- "Prep is the regulatory autopilot for food service."
- Architecture slide showing Federal → State → City → Facility chain.
- "We ingest the federal accreditation data, normalize state code like California's CalCode, then fuse local ordinances for cities like Los Angeles."
- "Operators log in, tell us what they're cooking, and Prep tells them exactly which permits, inspections, and insurance they need — and when they're due."

## 2:00 – 2:45 — Traction & Business Model
- "Today Prep tracks compliance for 62 kitchens across 8 cities."
- "We're adding California state coverage next month and rolling out subscription tiers for multi-location operators."
- Pricing slide: Core platform $299/site/month, State add-ons $99, Enterprise API contact sales.
- "Churn is zero so far because losing Prep means losing visibility into critical inspections."

## 2:45 – 3:00 — Ask & Vision
- "We're raising $1.2M to expand state coverage and build enterprise integrations."
- "Prep becomes the regulatory OS for every food brand scaling across state lines."
- End with product screenshot montage.

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

## Closing Line
"Prep keeps every kitchen inspection-ready so founders can focus on serving food, not reading regulatory PDFs."

