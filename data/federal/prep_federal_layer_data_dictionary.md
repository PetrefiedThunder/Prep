# Prep Federal Regulatory Layer - Data Dictionary

**Version:** 1.0
**Last Updated:** 2025-10-30
**Purpose:** Federal compliance backbone for the Prep Regulatory Engine

---

## Overview

This data dictionary describes the federal regulatory compliance data layer that encodes the authority chain from FDA oversight down to on-the-ground certification for food safety programs under FSMA (Food Safety Modernization Act).

The data model consists of four core tables representing:
1. **Accreditation Bodies (AB)** - FDA-recognized entities that accredit certifiers
2. **Certification Bodies (CB)** - Third-party auditors that certify facilities
3. **Scopes** - Food safety program areas (PCHF, PCAF, Produce Safety, etc.)
4. **Links** - Relationships between ABs, CBs, and Scopes with validity periods

---

## Table: `accreditation_bodies`

FDA-recognized accreditation bodies authorized to accredit third-party certification bodies under the Third-Party Certification Program (21 CFR Part 1, Subpart M).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique identifier for the accreditation body |
| `name` | TEXT | UNIQUE, NOT NULL | Official name of the accreditation body (e.g., "ANSI National Accreditation Board") |
| `url` | TEXT | NULLABLE | Official website URL for the accreditation body |
| `email` | TEXT | NULLABLE | Primary contact email address |
| `contact` | TEXT | NULLABLE | Contact person or department name |

**Indexes:** Primary key index on `id`

**Source:** FDA List of Accredited Third-Party Certification Bodies

**Example Row:**
```
id: 1
name: ANSI National Accreditation Board (ANAB)
url: https://anab.ansi.org
email: info@anab.ansi.org
contact: ANAB Accreditation Services
```

---

## Table: `certification_bodies`

Third-party auditors accredited by recognized accreditation bodies to conduct food safety audits and issue certifications.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique identifier for the certification body |
| `name` | TEXT | UNIQUE, NOT NULL | Official name of the certification body |
| `url` | TEXT | NULLABLE | Official website URL |
| `email` | TEXT | NULLABLE | Primary contact email for food safety certification services |

**Indexes:** Primary key index on `id`

**Source:** ANAB and IAS directories of accredited certification bodies

**Example Row:**
```
id: 1
name: NSF International Strategic Registrations
url: https://www.nsf.org
email: info@nsf.org
```

---

## Table: `scopes`

Food safety program areas recognized by FDA under FSMA and related regulations. Each scope represents a distinct certification domain with specific regulatory requirements.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique identifier for the scope |
| `name` | TEXT | UNIQUE, NOT NULL | Official name of the food safety scope (e.g., "Preventive Controls for Human Food") |
| `cfr_title_part_section` | TEXT | NULLABLE | Code of Federal Regulations citation (format: "XX CFR XXX") |
| `program_reference` | TEXT | NULLABLE | Common program name or reference (e.g., "FSMA Preventive Controls") |
| `notes` | TEXT | NULLABLE | Additional information about scope applicability and requirements |

**Indexes:** Primary key index on `id`

**Source:** FDA FSMA regulations and guidance documents

**Example Row:**
```
id: 1
name: Preventive Controls for Human Food (PCHF)
cfr_title_part_section: 21 CFR 117
program_reference: FSMA Preventive Controls
notes: Facilities manufacturing/processing/packing/holding food for human consumption
```

**Scope Values:**
1. **Preventive Controls for Human Food (PCHF)** - 21 CFR 117
2. **Preventive Controls for Animal Food (PCAF)** - 21 CFR 507
3. **Produce Safety** - 21 CFR 112
4. **Seafood HACCP** - 21 CFR 123
5. **Juice HACCP** - 21 CFR 120
6. **Low-Acid Canned Foods (LACF)** - 21 CFR 113
7. **Acidified Foods** - 21 CFR 114
8. **Infant Formula** - 21 CFR 106 and 107

---

## Table: `ab_cb_scope_links`

Junction table that establishes the relationship between accreditation bodies, certification bodies, and scopes. Each record represents an authorized certification scope with validity dates.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Unique identifier for the link |
| `accreditation_body_id` | INTEGER | NOT NULL, FOREIGN KEY | References `accreditation_bodies(id)` |
| `certification_body_id` | INTEGER | NOT NULL, FOREIGN KEY | References `certification_bodies(id)` |
| `scope_id` | INTEGER | NOT NULL, FOREIGN KEY | References `scopes(id)` |
| `recognition_initial_date` | DATE | NULLABLE | Date when the scope recognition was initially granted (format: YYYY-MM-DD) |
| `recognition_expiration_date` | DATE | NULLABLE | Date when the scope recognition expires (format: YYYY-MM-DD) |
| `scope_status` | TEXT | NULLABLE | Current status of the recognition: `active`, `suspended`, `expired`, `pending`, `withdrawn` |
| `source` | TEXT | NULLABLE | Data source reference (e.g., "ANAB Directory", "IAS Directory") |

**Indexes:**
- Primary key index on `id`
- Index on `recognition_expiration_date` (for expiration monitoring)
- Index on `scope_id` (for scope-based queries)
- Index on `accreditation_body_id` (for AB-based queries)
- Index on `certification_body_id` (for CB-based queries)

**Foreign Key Constraints:**
- `accreditation_body_id` → `accreditation_bodies(id)`
- `certification_body_id` → `certification_bodies(id)`
- `scope_id` → `scopes(id)`

**Example Row:**
```
id: 1
accreditation_body_id: 1
certification_body_id: 1
scope_id: 1
recognition_initial_date: 2020-06-15
recognition_expiration_date: 2026-06-15
scope_status: active
source: ANAB Directory
```

**Status Values:**
- `active` - Currently valid and in good standing
- `suspended` - Temporarily suspended by accreditation body
- `expired` - Recognition period has ended
- `pending` - Application submitted, awaiting approval
- `withdrawn` - Voluntarily withdrawn by certification body

---

## Supplementary Data Files

### `prep_federal_certifiers_normalized.csv`

Master denormalized dataset combining all entities for easy ingestion and reporting.

**Columns:**
- `link_id` - Unique link identifier
- `accreditation_body_id` - Accreditation body ID
- `accreditation_body_name` - Accreditation body name
- `certification_body_id` - Certification body ID
- `certification_body_name` - Certification body name
- `scope_id` - Scope ID
- `scope_name` - Scope name
- `cfr_title_part_section` - CFR citation
- `recognition_initial_date` - Initial recognition date
- `recognition_expiration_date` - Expiration date
- `scope_status` - Status
- `source` - Data source

### `scope_to_regulatory_anchor_scaffold.csv`

Enrichment data mapping scopes to regulatory citations and enforcement dates.

**Columns:**
- `scope_id` - Foreign key to scopes table
- `scope_name` - Scope name
- `cfr_title` - CFR Title number (e.g., 21)
- `cfr_part` - CFR Part number (e.g., 117)
- `cfr_section` - CFR Section (if applicable)
- `fda_guidance_url` - Link to FDA guidance document
- `fsma_final_rule_date` - Date when final rule was published
- `enforcement_date` - Date when enforcement began
- `state_adoption_notes` - State-level adoption information

---

## Data Maintenance

### Update Frequency
- **Weekly:** Check ANAB and IAS directories for new certifications or changes
- **Monthly:** Validate expiration dates and update status fields
- **Quarterly:** Reconcile with FDA's official Third-Party Certification Program list

### Validation Rules
1. All active links must have `recognition_expiration_date >= CURRENT_DATE`
2. All foreign key relationships must be valid
3. `scope_status` must be one of: active, suspended, expired, pending, withdrawn
4. Date fields must follow ISO 8601 format (YYYY-MM-DD)
5. CFR citations must match pattern: `\d+ CFR \d+`

### Data Quality Checks
- No orphaned records in junction table
- All active certifications have valid expiration dates in the future
- Each certification body has at least one scope
- Email addresses are valid format
- URLs are valid and accessible

---

## Integration Notes

### Linking to State/Local Data
This federal layer serves as the top-level authority chain. To complete the regulatory graph:

1. **State Health Departments** - Link facilities to state permits via `jurisdiction_code`
2. **County Health Inspections** - Map inspection records to facilities
3. **Facility Certifications** - Connect facility records to certification bodies and scopes

### API Design Considerations
The data model supports these common API patterns:

- **GET /federal/scopes** - List all available scopes
- **GET /federal/certifiers?scope={scope_name}** - Find certifiers by scope
- **GET /federal/certifiers/{id}/scopes** - Get all scopes for a certifier
- **GET /federal/certifiers/{id}/validity** - Check current validity status
- **GET /federal/expiring?days={n}** - Find expirations within n days

### Graph Database Mapping
For Neo4j or similar graph databases:

**Nodes:**
- `(:AccreditationBody)` with properties from `accreditation_bodies`
- `(:CertificationBody)` with properties from `certification_bodies`
- `(:Scope)` with properties from `scopes`
- `(:Facility)` - to be linked in application

**Relationships:**
- `(:AccreditationBody)-[:ACCREDITS {since, until, status}]->(:CertificationBody)`
- `(:CertificationBody)-[:AUTHORIZED_FOR {since, until, status}]->(:Scope)`
- `(:Facility)-[:CERTIFIED_BY {date, certificate_id}]->(:CertificationBody)`
- `(:Facility)-[:REQUIRES]->(:Scope)` based on activity type

---

## Glossary

**AB (Accreditation Body)** - Entity recognized by FDA to accredit third-party certification bodies.

**CB (Certification Body)** - Third-party auditor accredited to conduct food safety audits and issue certifications.

**CFR (Code of Federal Regulations)** - Codification of rules and regulations published by executive departments and agencies of the federal government.

**FSMA (Food Safety Modernization Act)** - Public Law 111-353, signed January 4, 2011, overhauling U.S. food safety system.

**HACCP (Hazard Analysis and Critical Control Points)** - Systematic preventive approach to food safety.

**LACF (Low-Acid Canned Foods)** - Foods with a pH greater than 4.6 and water activity greater than 0.85, processed in hermetically sealed containers.

**PCAF (Preventive Controls for Animal Food)** - FSMA rule for facilities that manufacture, process, pack, or hold food for animals.

**PCHF (Preventive Controls for Human Food)** - FSMA rule for facilities that manufacture, process, pack, or hold food for human consumption.

**Scope** - Specific food safety program area for which a certification body is accredited (e.g., PCHF, Produce Safety).

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-30 | Initial release - Federal compliance backbone with 2 ABs, 15 CBs, 8 scopes, 34 links |

---

## Contact & Support

For questions about this data layer:
- **Technical issues:** See repository documentation
- **Data accuracy:** Refer to FDA's official Third-Party Certification Program list
- **Regulatory interpretation:** Consult FDA guidance documents or legal counsel
