# City Regulations Database Schema

## Overview

This database schema supports city-level compliance regulations for food preparation, restaurant certification, business licenses, and insurance requirements across major US cities.

**Target Cities:**
- New York, NY
- San Francisco, CA
- Chicago, IL
- Atlanta, GA
- Los Angeles, CA
- Seattle, WA
- Portland, OR
- Boston, MA

## Database Tables

### 1. city_jurisdictions

**Purpose:** Store information about city jurisdictions and their regulatory departments

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(36) | PRIMARY KEY | UUID identifier |
| city_name | VARCHAR | NOT NULL, INDEX | City name |
| state | VARCHAR(2) | NOT NULL, INDEX | Two-letter state code |
| county | VARCHAR | NULL | County name |
| country_code | VARCHAR(2) | DEFAULT 'US' | Country code |
| fips_code | VARCHAR | NULL | Federal Information Processing Standards code |
| population | INTEGER | NULL | City population |
| health_department_name | VARCHAR | NULL | Name of health department |
| health_department_url | VARCHAR | NULL | Health department website |
| business_licensing_dept | VARCHAR | NULL | Name of business licensing department |
| business_licensing_url | VARCHAR | NULL | Business licensing website |
| fire_department_name | VARCHAR | NULL | Name of fire department |
| fire_department_url | VARCHAR | NULL | Fire department website |
| phone | VARCHAR | NULL | Main contact phone |
| email | VARCHAR | NULL | Main contact email |
| address | VARCHAR | NULL | Department address |
| timezone | VARCHAR | DEFAULT 'America/New_York' | City timezone |
| created_at | DATETIME | DEFAULT NOW() | Record creation timestamp |
| updated_at | DATETIME | DEFAULT NOW() | Last update timestamp |
| data_source | VARCHAR | NULL | Source of the data |
| last_verified | DATETIME | NULL | Last verification date |

**Indexes:**
- `idx_city_state`: (city_name, state)

---

### 2. city_regulations

**Purpose:** Store city-specific regulatory requirements

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(36) | PRIMARY KEY | UUID identifier |
| city_id | VARCHAR(36) | FOREIGN KEY, NOT NULL, INDEX | Reference to city_jurisdictions.id |
| regulation_type | VARCHAR | NOT NULL, INDEX | Type of regulation (enum) |
| title | VARCHAR | NOT NULL | Regulation title |
| description | TEXT | NULL | Detailed description |
| local_code_reference | VARCHAR | NULL | Local code/ordinance reference |
| cfr_citation | VARCHAR | NULL | Federal CFR citation (if applicable) |
| state_code_reference | VARCHAR | NULL | State code reference (if applicable) |
| effective_date | DATETIME | NULL | When regulation takes effect |
| expiration_date | DATETIME | NULL | When regulation expires |
| renewal_period_days | INTEGER | NULL | Renewal period in days |
| enforcement_agency | VARCHAR | NOT NULL | Agency responsible for enforcement |
| agency_contact | VARCHAR | NULL | Contact person at agency |
| agency_phone | VARCHAR | NULL | Agency phone number |
| agency_url | VARCHAR | NULL | Agency website URL |
| penalty_for_violation | TEXT | NULL | Description of penalties |
| fine_amount_min | FLOAT | NULL | Minimum fine amount (USD) |
| fine_amount_max | FLOAT | NULL | Maximum fine amount (USD) |
| requirements | JSON | NULL | Structured requirement details |
| application_process | JSON | NULL | Application process steps |
| required_documents | JSON | NULL | List of required documents |
| fees | JSON | NULL | Fee structure |
| applicable_facility_types | JSON | NOT NULL | List of applicable facility types |
| employee_count_threshold | INTEGER | NULL | Minimum employee count for applicability |
| revenue_threshold | FLOAT | NULL | Minimum revenue for applicability |
| is_active | BOOLEAN | DEFAULT TRUE | Whether regulation is currently active |
| priority | VARCHAR | DEFAULT 'medium' | Priority level (critical/high/medium/low) |
| created_at | DATETIME | DEFAULT NOW() | Record creation timestamp |
| updated_at | DATETIME | DEFAULT NOW() | Last update timestamp |
| data_source | VARCHAR | NULL | Source of the data |
| last_verified | DATETIME | NULL | Last verification date |
| notes | TEXT | NULL | Additional notes |

**Indexes:**
- `idx_city_regulation_type`: (city_id, regulation_type)
- `idx_regulation_active`: (is_active)

**Regulation Types:**
- `health_permit`: Health department permit
- `business_license`: General business license
- `food_handler_certification`: Food handler certification
- `fire_safety`: Fire safety inspection/permit
- `building_permit`: Building/construction permit
- `zoning`: Zoning compliance
- `parking`: Parking requirements
- `signage`: Signage permits
- `waste_management`: Waste management requirements
- `insurance`: Insurance requirements
- `workers_compensation`: Workers comp insurance
- `liability_insurance`: Liability insurance
- `alcohol_license`: Alcohol service license
- `grease_trap`: Grease trap requirements
- `food_safety_training`: Food safety training

---

### 3. city_insurance_requirements

**Purpose:** Store insurance requirement details by city and facility type

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(36) | PRIMARY KEY | UUID identifier |
| city_id | VARCHAR(36) | FOREIGN KEY, NOT NULL, INDEX | Reference to city_jurisdictions.id |
| insurance_type | VARCHAR | NOT NULL | Type of insurance |
| coverage_name | VARCHAR | NOT NULL | Name of coverage |
| description | TEXT | NULL | Coverage description |
| minimum_coverage_amount | FLOAT | NOT NULL | Minimum coverage in USD |
| per_occurrence_limit | FLOAT | NULL | Per-occurrence limit |
| aggregate_limit | FLOAT | NULL | Aggregate limit |
| deductible_max | FLOAT | NULL | Maximum deductible |
| applicable_facility_types | JSON | NOT NULL | List of applicable facility types |
| employee_count_threshold | INTEGER | NULL | Minimum employee count |
| local_ordinance | VARCHAR | NULL | Local ordinance reference |
| state_requirement | VARCHAR | NULL | State requirement reference |
| is_mandatory | BOOLEAN | DEFAULT TRUE | Whether coverage is mandatory |
| effective_date | DATETIME | NULL | Effective date |
| created_at | DATETIME | DEFAULT NOW() | Record creation timestamp |
| updated_at | DATETIME | DEFAULT NOW() | Last update timestamp |
| notes | TEXT | NULL | Additional notes |

**Indexes:**
- `idx_city_insurance_type`: (city_id, insurance_type)

**Insurance Types:**
- `general_liability`: General liability insurance
- `workers_compensation`: Workers compensation
- `product_liability`: Product liability
- `property_insurance`: Property insurance
- `business_interruption`: Business interruption insurance
- `umbrella_policy`: Umbrella/excess liability

---

### 4. city_permit_applications

**Purpose:** Store permit application processes and timelines

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(36) | PRIMARY KEY | UUID identifier |
| city_id | VARCHAR(36) | FOREIGN KEY, NOT NULL, INDEX | Reference to city_jurisdictions.id |
| regulation_id | VARCHAR(36) | FOREIGN KEY, NOT NULL | Reference to city_regulations.id |
| permit_name | VARCHAR | NOT NULL | Name of the permit |
| application_url | VARCHAR | NULL | Online application URL |
| submission_method | JSON | NULL | Submission methods (online/mail/in-person) |
| processing_time_days | INTEGER | NULL | Typical processing time in days |
| processing_time_notes | TEXT | NULL | Notes about processing time |
| application_fee | FLOAT | NULL | Application fee amount |
| renewal_fee | FLOAT | NULL | Renewal fee amount |
| late_fee | FLOAT | NULL | Late fee amount |
| prerequisite_permits | JSON | NULL | IDs of required prerequisite permits |
| required_inspections | JSON | NULL | Required inspections |
| responsible_dept | VARCHAR | NULL | Responsible department |
| contact_phone | VARCHAR | NULL | Contact phone |
| contact_email | VARCHAR | NULL | Contact email |
| created_at | DATETIME | DEFAULT NOW() | Record creation timestamp |
| updated_at | DATETIME | DEFAULT NOW() | Last update timestamp |

**Indexes:**
- `idx_city_permit`: (city_id, regulation_id)

---

### 5. facility_compliance_status

**Purpose:** Track compliance status for facilities in each city

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR(36) | PRIMARY KEY | UUID identifier |
| facility_id | VARCHAR | NOT NULL, INDEX | Kitchen/facility ID from main system |
| city_id | VARCHAR(36) | FOREIGN KEY, NOT NULL, INDEX | Reference to city_jurisdictions.id |
| regulation_id | VARCHAR(36) | FOREIGN KEY, NOT NULL, INDEX | Reference to city_regulations.id |
| compliance_status | VARCHAR | NOT NULL | Compliance status (enum) |
| last_check_date | DATETIME | NOT NULL | Last compliance check date |
| next_check_due | DATETIME | NULL | Next check due date |
| permit_number | VARCHAR | NULL | Permit/license number |
| issue_date | DATETIME | NULL | Date permit was issued |
| expiration_date | DATETIME | NULL | Permit expiration date |
| has_violations | BOOLEAN | DEFAULT FALSE | Whether violations exist |
| violation_count | INTEGER | DEFAULT 0 | Number of violations |
| violation_details | JSON | NULL | Details of violations |
| last_inspector_name | VARCHAR | NULL | Name of last inspector |
| last_inspection_score | INTEGER | NULL | Last inspection score |
| created_at | DATETIME | DEFAULT NOW() | Record creation timestamp |
| updated_at | DATETIME | DEFAULT NOW() | Last update timestamp |
| notes | TEXT | NULL | Additional notes |

**Indexes:**
- `idx_facility_compliance`: (facility_id, city_id, regulation_id)
- `idx_compliance_status`: (compliance_status)
- `idx_expiration_date`: (expiration_date)

**Compliance Status Values:**
- `compliant`: Fully compliant
- `non_compliant`: Not in compliance
- `pending_review`: Pending review
- `expired`: Expired permit/certification
- `suspended`: Suspended status
- `not_required`: Not required for this facility

---

## Facility Types

The following facility types are supported:

- `commercial_kitchen`: Commercial kitchen
- `ghost_kitchen`: Ghost/cloud kitchen
- `restaurant`: Full-service restaurant
- `catering`: Catering operation
- `food_truck`: Mobile food service
- `bakery`: Bakery
- `commissary`: Commissary kitchen
- `prep_kitchen`: Prep kitchen

---

## JSON Field Structures

### requirements (in city_regulations)

```json
{
  "facility_requirements": {
    "min_square_feet": 500,
    "required_equipment": ["commercial sink", "fire suppression", "refrigeration"],
    "ventilation": "Type I hood required",
    "flooring": "Non-porous, washable surface"
  },
  "staffing_requirements": {
    "certified_food_manager": true,
    "food_handler_certs": "all staff"
  },
  "operational_requirements": {
    "hours_restriction": null,
    "noise_limits": null
  }
}
```

### application_process (in city_regulations)

```json
{
  "steps": [
    {
      "step_number": 1,
      "description": "Complete online application",
      "url": "https://..."
    },
    {
      "step_number": 2,
      "description": "Submit floor plans",
      "required_documents": ["floor_plan.pdf", "equipment_layout.pdf"]
    },
    {
      "step_number": 3,
      "description": "Schedule pre-opening inspection",
      "contact": "555-1234"
    }
  ],
  "estimated_timeline": "4-6 weeks"
}
```

### fees (in city_regulations)

```json
{
  "application_fee": 250.00,
  "annual_renewal": 175.00,
  "late_renewal_penalty": 50.00,
  "inspection_fee": 100.00,
  "reinspection_fee": 150.00
}
```

### violation_details (in facility_compliance_status)

```json
{
  "violations": [
    {
      "violation_code": "FS-101",
      "description": "Temperature logs not maintained",
      "severity": "medium",
      "noted_date": "2024-03-15",
      "corrected": false,
      "correction_deadline": "2024-04-01"
    }
  ]
}
```

---

## Data Ingestion Process

### 1. Initial City Setup

```sql
INSERT INTO city_jurisdictions (...)
VALUES (...);
```

### 2. Add Regulations

```sql
INSERT INTO city_regulations (
  city_id,
  regulation_type,
  title,
  ...
) VALUES (...);
```

### 3. Add Insurance Requirements

```sql
INSERT INTO city_insurance_requirements (...)
VALUES (...);
```

### 4. Track Facility Compliance

```sql
INSERT INTO facility_compliance_status (
  facility_id,
  city_id,
  regulation_id,
  compliance_status,
  ...
) VALUES (...);
```

---

## Integration with Federal Layer

City regulations can reference federal requirements via the `cfr_citation` field:

```sql
SELECT cr.*, fr.scope_name, fr.program_reference
FROM city_regulations cr
LEFT JOIN federal_scopes fr ON cr.cfr_citation = fr.cfr_title_part_section
WHERE cr.city_id = ?;
```

This creates the regulatory chain:
**Federal Scope → State Code → City Ordinance → Facility Compliance**

---

## Query Examples

### Get all regulations for a city

```sql
SELECT r.*, j.city_name, j.state
FROM city_regulations r
JOIN city_jurisdictions j ON r.city_id = j.id
WHERE j.city_name = 'San Francisco' AND j.state = 'CA'
AND r.is_active = TRUE;
```

### Check facility compliance in a city

```sql
SELECT
  r.regulation_type,
  r.title,
  fcs.compliance_status,
  fcs.expiration_date
FROM facility_compliance_status fcs
JOIN city_regulations r ON fcs.regulation_id = r.id
JOIN city_jurisdictions j ON fcs.city_id = j.id
WHERE fcs.facility_id = ?
AND j.city_name = ?
AND j.state = ?;
```

### Find expiring permits

```sql
SELECT
  fcs.facility_id,
  r.title,
  fcs.expiration_date,
  j.city_name
FROM facility_compliance_status fcs
JOIN city_regulations r ON fcs.regulation_id = r.id
JOIN city_jurisdictions j ON fcs.city_id = j.id
WHERE fcs.expiration_date BETWEEN date('now') AND date('now', '+30 days')
ORDER BY fcs.expiration_date;
```

### Get insurance requirements for facility type

```sql
SELECT
  ir.*,
  j.city_name,
  j.state
FROM city_insurance_requirements ir
JOIN city_jurisdictions j ON ir.city_id = j.id
WHERE j.city_name = ?
AND j.state = ?
AND json_extract(ir.applicable_facility_types, '$') LIKE '%ghost_kitchen%';
```

---

## Data Verification Workflow

1. **Initial Data Collection**: Gather regulations from city sources
2. **Data Entry**: Use ETL pipeline to ingest structured data
3. **Verification**: Set `last_verified` timestamp
4. **Monitoring**: Track `expiration_date` for permit renewals
5. **Updates**: Re-verify regulations quarterly, update `updated_at`

---

## Data Sources to Collect

For each city, gather from:

1. **Health Department**
   - Food service establishment permits
   - Health inspection requirements
   - Food handler certifications

2. **Business Licensing**
   - Business license requirements
   - Fee schedules
   - Application processes

3. **Fire Department**
   - Fire safety inspections
   - Fire suppression requirements
   - Emergency exit requirements

4. **Building/Planning Department**
   - Zoning requirements
   - Building permits
   - Occupancy limits

5. **Insurance Requirements**
   - Minimum coverage amounts
   - Required policy types
   - Proof of insurance process

---

## Next Steps

1. Run `database.py` to initialize the database
2. Use the ETL pipeline to ingest collected regulatory data
3. Verify data completeness for each city
4. Start the FastAPI service to expose the data
5. Integrate with Prep's compliance engine
