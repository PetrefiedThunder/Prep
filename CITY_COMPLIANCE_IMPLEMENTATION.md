# City Compliance Layer Implementation

## Overview

The city compliance layer extends Prep's regulatory engine to include city-level regulations for food preparation facilities across 8 major US cities: New York, San Francisco, Chicago, Atlanta, Los Angeles, Seattle, Portland, and Boston.

This implementation provides a complete regulatory chain from federal requirements down to city ordinances, enabling facilities to verify compliance across all jurisdictional levels.

## Architecture

### Regulatory Hierarchy

```
┌────────────────────────────────────────┐
│    Federal Layer (FSMA, FDA, CFR)      │
│  ✓ Implemented (FEDERAL_LAYER_*.md)   │
└────────────────────────────────────────┘
                   ↓
┌────────────────────────────────────────┐
│         State Layer (State Codes)       │
│        ◯ Partially Implemented         │
└────────────────────────────────────────┘
                   ↓
┌────────────────────────────────────────┐
│    City Layer (Local Ordinances) ← NEW │
│        ✓ This Implementation           │
└────────────────────────────────────────┘
                   ↓
┌────────────────────────────────────────┐
│      Facility Compliance Status        │
└────────────────────────────────────────┘
```

### Components

```
apps/city_regulatory_service/
├── main.py                      # FastAPI service
├── models.py                    # Data models & schemas
├── database.py                  # DB initialization
├── etl.py                       # Data ingestion pipeline
├── federal_integration.py       # Federal layer integration
├── requirements.txt
└── tests/
    ├── test_service.py
    └── test_compliance_engine.py

prep/compliance/
└── city_compliance_engine.py    # Compliance validation engine

data/cities/
├── prep_city_regulations.sqlite # Regulatory database
└── schemas/
    └── city_regulations_schema.md
```

---

## Database Schema

### Core Tables

#### 1. `city_jurisdictions`
Stores city information and regulatory department contacts.

**Key Fields:**
- `city_name`, `state`, `county`
- `health_department_name`, `health_department_url`
- `business_licensing_dept`, `business_licensing_url`
- `fire_department_name`, `fire_department_url`

**8 Cities Configured:**
- New York, NY
- San Francisco, CA
- Chicago, IL
- Atlanta, GA
- Los Angeles, CA
- Seattle, WA
- Portland, OR
- Boston, MA

#### 2. `city_regulations`
Stores city-specific regulatory requirements.

**Key Fields:**
- `regulation_type`: health_permit, business_license, fire_safety, insurance, etc.
- `title`, `description`
- `local_code_reference`: City ordinance/code reference
- `cfr_citation`: Links to federal scope (e.g., "21 CFR 117")
- `enforcement_agency`: Department responsible
- `requirements`: JSON - Detailed requirements
- `fees`: JSON - Fee structure
- `applicable_facility_types`: JSON array
- `priority`: critical, high, medium, low

**Regulation Types:**
- Health permits & certifications
- Business licenses
- Fire safety inspections
- Insurance requirements
- Food handler certifications
- Zoning & building permits
- Environmental compliance (grease trap, waste)

#### 3. `city_insurance_requirements`
Insurance coverage requirements by city and facility type.

**Key Fields:**
- `insurance_type`: general_liability, workers_comp, product_liability
- `minimum_coverage_amount`: Required coverage in USD
- `per_occurrence_limit`, `aggregate_limit`
- `applicable_facility_types`
- `is_mandatory`: Boolean

#### 4. `facility_compliance_status`
Tracks compliance status for individual facilities.

**Key Fields:**
- `facility_id`: Links to kitchen in main system
- `regulation_id`: Links to city_regulations
- `compliance_status`: compliant, non_compliant, expired, suspended
- `permit_number`, `expiration_date`
- `violation_details`: JSON

---

## API Endpoints

### City Regulatory Service (Port 8002)

#### City Information
```bash
GET /cities                          # List all supported cities
GET /cities?state=CA                 # Filter by state
GET /city/{city_name}/{state}       # Get city details
```

#### Regulations
```bash
GET /city/{city}/regulations                    # All regulations
GET /city/{city}/regulations?regulation_type=health_permit
GET /city/{city}/regulations?facility_type=commercial_kitchen
GET /city/{city}/regulations?priority=critical
GET /city/{city}/regulations/summary            # Statistics
```

#### Insurance Requirements
```bash
GET /city/{city}/insurance-requirements
GET /city/{city}/insurance-requirements?mandatory_only=true
GET /city/{city}/insurance-requirements?facility_type=ghost_kitchen
```

#### Compliance Checking
```bash
POST /city/{city}/compliance-check
```

**Request Body:**
```json
{
  "facility_id": "kitchen-123",
  "facility_type": "commercial_kitchen",
  "employee_count": 5,
  "current_permits": [
    {
      "type": "health_permit",
      "number": "HP-2024-001",
      "expiration_date": "2025-12-31"
    }
  ],
  "current_insurance": [
    {
      "type": "general_liability",
      "coverage_amount": 1000000
    }
  ]
}
```

**Response:**
```json
{
  "overall_compliant": true,
  "compliance_score": 95.0,
  "required_regulations": [...],
  "compliant_regulations": ["reg-1", "reg-2"],
  "non_compliant_regulations": [],
  "missing_requirements": [],
  "insurance_compliant": true,
  "recommended_actions": [],
  "estimated_cost_to_comply": 0,
  "check_timestamp": "2024-11-01T00:00:00Z"
}
```

#### Data Ingestion
```bash
POST /city/data/ingest
```

For bulk importing regulatory data (see Data Ingestion Guide below).

---

## City Compliance Engine

### Purpose
Validates facility data against city-level compliance rules.

### Usage

```python
from prep.compliance.city_compliance_engine import CityComplianceEngine

# Initialize engine
engine = CityComplianceEngine(
    city_name="San Francisco",
    state="CA",
    facility_type="commercial_kitchen"
)

# Load rules
engine.load_rules()

# Validate facility data
facility_data = {
    "facility_id": "kitchen-123",
    "health_permit": {...},
    "business_license": {...},
    "insurance": [...],
    "certifications": [...],
    "fire_safety": {...},
    # ... more fields
}

violations = engine.validate(facility_data)

# Generate report
report = engine.generate_report(facility_data)
print(f"Compliance Score: {report.overall_compliance_score * 100}%")
print(f"Violations: {len(report.violations_found)}")
```

### Compliance Rules

The engine validates 10 key compliance areas:

| Rule ID | Category | Severity | Description |
|---------|----------|----------|-------------|
| CITY-HEALTH-001 | Health & Safety | Critical | Valid health permit |
| CITY-BIZ-001 | Business | Critical | Valid business license |
| CITY-INS-001 | Insurance | Critical | General liability insurance ($1M min) |
| CITY-INS-002 | Insurance | Critical | Workers compensation (if employees) |
| CITY-CERT-001 | Certifications | High | Food handler certifications |
| CITY-FIRE-001 | Fire Safety | Critical | Fire safety inspection |
| CITY-CERT-002 | Certifications | High | Food safety manager on staff |
| CITY-ENV-001 | Environmental | Medium | Grease trap maintenance |
| CITY-ENV-002 | Environmental | Medium | Waste disposal compliance |
| CITY-ADMIN-001 | Administrative | High | Timely permit renewals |

---

## Federal Integration

### Regulatory Chain Linking

City regulations can reference federal scopes via CFR citations:

```
Federal:  21 CFR 117 (PCHF - Preventive Controls for Human Food)
    ↓
State:    CA Health Code § 113000
    ↓
City:     SF Health Code § 4700-4753
    ↓
Facility: Must comply with all layers
```

### Integration Features

```python
from apps.city_regulatory_service.federal_integration import FederalRegulatoryIntegration

integration = FederalRegulatoryIntegration()

# Link city regulation to federal scope
await integration.link_city_regulation_to_federal(
    regulation_id="reg-123",
    cfr_citation="21 CFR 117"
)

# Get complete regulatory chain
chain = await integration.get_complete_regulatory_chain(
    city_name="San Francisco",
    state="CA"
)

# Get authorized certifiers for city requirements
certifiers = await integration.get_recommended_certifiers(
    city_name="San Francisco",
    state="CA",
    facility_type="commercial_kitchen"
)
```

---

## Data Ingestion Guide

### For Your Team: How to Add Collected Regulatory Data

You mentioned gathering city-level regulations for the 8 cities. Here's how to ingest that data into the system:

### Option 1: JSON File Import

**Step 1:** Structure your data as JSON

```json
{
  "city_info": {
    "city_name": "San Francisco",
    "state": "CA",
    "county": "San Francisco County",
    "health_department_name": "SF Department of Public Health",
    "health_department_url": "https://www.sfdph.org/"
  },
  "regulations": [
    {
      "regulation_type": "health_permit",
      "title": "Food Service Establishment Permit",
      "description": "Required for all food service operations",
      "local_code_reference": "SF Health Code § 4700",
      "cfr_citation": "21 CFR 117",
      "enforcement_agency": "SF Department of Public Health",
      "agency_url": "https://www.sfdph.org/dph/EH/Food/",
      "priority": "critical",
      "applicable_facility_types": [
        "commercial_kitchen",
        "ghost_kitchen",
        "restaurant"
      ],
      "requirements": {
        "facility_requirements": {
          "min_square_feet": 500,
          "required_equipment": ["commercial sink", "fire suppression"]
        },
        "staffing_requirements": {
          "certified_food_manager": true
        }
      },
      "fees": {
        "application_fee": 458.00,
        "annual_renewal": 458.00
      },
      "renewal_period_days": 365,
      "is_active": true
    }
  ],
  "insurance_requirements": [
    {
      "insurance_type": "general_liability",
      "coverage_name": "Commercial General Liability",
      "minimum_coverage_amount": 1000000.00,
      "per_occurrence_limit": 1000000.00,
      "aggregate_limit": 2000000.00,
      "applicable_facility_types": [
        "commercial_kitchen",
        "ghost_kitchen"
      ],
      "is_mandatory": true
    }
  ]
}
```

**Step 2:** Run the ETL script

```bash
python -c "
from apps.city_regulatory_service.etl import CityRegulatoryETL

etl = CityRegulatoryETL()
stats = etl.load_from_json('data/cities/san_francisco_ca.json')
print(stats)
etl.close()
"
```

### Option 2: CSV Import

**Step 1:** Create CSV files

**regulations.csv:**
```csv
regulation_type,title,description,local_code_reference,enforcement_agency,priority,applicable_facility_types,fees
health_permit,"Food Service Permit","Required permit","SF Code 4700","Health Dept",critical,"commercial_kitchen|ghost_kitchen","{\"application_fee\": 458.00}"
```

**insurance_requirements.csv:**
```csv
insurance_type,coverage_name,minimum_coverage_amount,applicable_facility_types,is_mandatory
general_liability,"Commercial GL",1000000.00,"commercial_kitchen|ghost_kitchen",true
```

**Step 2:** Import via ETL

```bash
python -c "
from apps.city_regulatory_service.etl import CityRegulatoryETL

etl = CityRegulatoryETL()
stats = etl.load_from_csv(
    city_name='San Francisco',
    state='CA',
    regulations_csv='data/cities/sf_regulations.csv',
    insurance_csv='data/cities/sf_insurance.csv'
)
print(stats)
etl.close()
"
```

### Option 3: Direct API Ingestion

```bash
curl -X POST http://localhost:8002/city/data/ingest \
  -H "Content-Type: application/json" \
  -d @san_francisco_data.json
```

### Option 4: Programmatic Bulk Update

```python
from apps.city_regulatory_service.etl import CityRegulatoryETL

etl = CityRegulatoryETL()

regulations_list = [
    {
        "regulation_type": "health_permit",
        "title": "Food Service Establishment Permit",
        # ... more fields
    },
    # ... more regulations
]

insurance_list = [
    {
        "insurance_type": "general_liability",
        # ... more fields
    }
]

stats = etl.bulk_update_city(
    city_name="San Francisco",
    state="CA",
    regulations=regulations_list,
    insurance_requirements=insurance_list
)

print(stats)
etl.close()
```

---

## Data Collection Template

### For Each City, Gather:

#### 1. Jurisdiction Information
- [ ] Health department name, URL, contact
- [ ] Business licensing department name, URL, contact
- [ ] Fire department name, URL, contact
- [ ] Main city contact number

#### 2. Health & Food Safety Regulations
- [ ] Food service establishment permit requirements
- [ ] Application process and timeline
- [ ] Fees (application, renewal, inspection)
- [ ] Required facility specifications
- [ ] Inspection frequency and process
- [ ] Food handler certification requirements
- [ ] Food safety manager requirements

#### 3. Business Licensing
- [ ] General business license requirements
- [ ] Application process
- [ ] Fees and renewal periods
- [ ] Required documentation

#### 4. Fire Safety
- [ ] Fire safety inspection requirements
- [ ] Fire suppression system requirements
- [ ] Inspection frequency
- [ ] Contact for scheduling inspections

#### 5. Insurance Requirements
- [ ] General liability coverage minimums
- [ ] Workers compensation requirements
- [ ] Product liability requirements
- [ ] Any other mandatory insurance

#### 6. Additional Permits
- [ ] Building/construction permits
- [ ] Zoning requirements
- [ ] Signage permits
- [ ] Grease trap requirements
- [ ] Waste management/recycling requirements

---

## Running the Service

### Start the City Regulatory Service

```bash
# From project root
cd apps/city_regulatory_service

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Initialize database (first time only)
python database.py

# Start the service
python main.py

# Service runs on http://localhost:8002
```

### Start with Docker (Future)

```bash
docker-compose up city-regulatory-service
```

---

## Testing

### Run Tests

```bash
# Install pytest
pip install pytest pytest-asyncio

# Run all tests
pytest apps/city_regulatory_service/tests/ -v

# Run specific test file
pytest apps/city_regulatory_service/tests/test_service.py -v

# Run compliance engine tests
pytest apps/city_regulatory_service/tests/test_compliance_engine.py -v
```

### Manual Testing

```bash
# Health check
curl http://localhost:8002/health

# List cities
curl http://localhost:8002/cities

# Get San Francisco regulations
curl "http://localhost:8002/city/San%20Francisco/CA/regulations"

# Check compliance
curl -X POST http://localhost:8002/city/San%20Francisco/CA/compliance-check \
  -H "Content-Type: application/json" \
  -d '{
    "facility_id": "test-123",
    "facility_type": "commercial_kitchen",
    "employee_count": 5,
    "current_permits": [],
    "current_insurance": []
  }'
```

---

## Integration with Prep Platform

### 1. Kitchen Compliance Validation

Update the kitchen onboarding flow to check city compliance:

```python
from apps.city_regulatory_service.main import check_facility_compliance

async def validate_kitchen_city_compliance(kitchen_id, city, state):
    # Get kitchen data
    kitchen = await db.get_kitchen(kitchen_id)

    # Check city compliance
    compliance = await check_facility_compliance(
        city_name=city,
        state=state,
        request={
            "facility_id": kitchen_id,
            "facility_type": kitchen.facility_type,
            "employee_count": kitchen.employee_count,
            "current_permits": kitchen.permits,
            "current_insurance": kitchen.insurance_policies,
        }
    )

    # Update kitchen compliance status
    kitchen.city_compliance_score = compliance.compliance_score
    kitchen.city_compliant = compliance.overall_compliant

    return compliance
```

### 2. Compliance Dashboard

Display city compliance status in kitchen dashboard:

```typescript
// Fetch compliance status
const cityCompliance = await fetch(
  `/city/${kitchen.city}/${kitchen.state}/compliance-check`,
  {
    method: 'POST',
    body: JSON.stringify({
      facility_id: kitchen.id,
      facility_type: kitchen.facilityType,
      employee_count: kitchen.employeeCount,
      current_permits: kitchen.permits,
      current_insurance: kitchen.insurance
    })
  }
);

// Display compliance badge
<ComplianceBadge
  score={cityCompliance.compliance_score}
  status={cityCompliance.overall_compliant ? 'compliant' : 'non-compliant'}
/>
```

### 3. Regulatory Requirements Checklist

Show kitchen owners what they need:

```typescript
const requirements = await fetch(
  `/city/${city}/${state}/regulations?facility_type=commercial_kitchen`
);

<RequirementsChecklist
  regulations={requirements}
  currentPermits={kitchen.permits}
/>
```

---

## Next Steps

### 1. Data Population ← **YOUR WORK**
Collect actual regulatory data from city sources and ingest using the ETL pipeline above.

### 2. Validation & Verification
Once data is ingested, verify accuracy with city sources.

### 3. Platform Integration
Integrate city compliance checking into:
- Kitchen onboarding flow
- Compliance dashboard
- Booking eligibility checks
- Safety badge calculations

### 4. Monitoring & Updates
Set up quarterly reviews to update:
- Regulation changes
- Fee updates
- New requirements
- Department contact changes

### 5. Expansion
After validating the 8 initial cities, expand to additional markets.

---

## Support & Documentation

- **Federal Layer:** See `FEDERAL_LAYER_IMPLEMENTATION.md`
- **Database Schema:** See `data/cities/schemas/city_regulations_schema.md`
- **API Docs:** http://localhost:8002/docs (when service is running)
- **Base Compliance Engine:** `prep/compliance/base_engine.py`

---

## Summary

✅ **Implemented:**
- City regulatory database for 8 cities
- Data models for regulations, insurance, permits
- FastAPI service with comprehensive endpoints
- City compliance engine with 10 validation rules
- Federal regulatory integration
- ETL pipeline for data ingestion
- Complete test suite

🔄 **Your Team's Work:**
- Collect actual regulatory data from city sources
- Populate database using ETL pipeline
- Verify data accuracy

🚀 **Ready for:**
- Integration with Prep platform
- Kitchen compliance validation
- Investor demo with real city data

The infrastructure is built and ready to receive your collected regulatory data!
