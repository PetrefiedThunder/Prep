# City Regulatory Data Ingestion Guide

## Quick Start

This guide shows you how to add the regulatory data you've collected for NYC, San Francisco, Chicago, Atlanta, Los Angeles, Seattle, Portland, and Boston into Prep's compliance engine.

---

## Data Collection Checklist

For each city, you're gathering:

✅ **Food Preparation & Health**
- Food service establishment permits
- Health inspection requirements
- Food handler certifications
- Food safety manager requirements

✅ **Business Licensing**
- General business licenses
- Application processes
- Fee schedules

✅ **Insurance Requirements**
- General liability minimums
- Workers compensation
- Product liability
- Other mandatory coverage

✅ **Operational Compliance**
- Fire safety inspections
- Building/zoning permits
- Environmental requirements

---

## Ingestion Methods

### Method 1: JSON File (Recommended)

**Best for:** Structured data with complete details

#### Template: `{city_name}_{state}.json`

```json
{
  "city_info": {
    "city_name": "San Francisco",
    "state": "CA",
    "county": "San Francisco County",
    "fips_code": "06075",
    "population": 873965,
    "health_department_name": "SF Department of Public Health",
    "health_department_url": "https://www.sfdph.org/",
    "business_licensing_dept": "SF Office of the Treasurer & Tax Collector",
    "business_licensing_url": "https://sftreasurer.org/",
    "fire_department_name": "SF Fire Department",
    "fire_department_url": "https://sf-fire.org/",
    "phone": "311",
    "timezone": "America/Los_Angeles"
  },
  "regulations": [
    {
      "regulation_type": "health_permit",
      "title": "Food Service Establishment Permit",
      "description": "All food service operations must obtain and maintain a valid health permit from the San Francisco Department of Public Health",
      "local_code_reference": "SF Health Code § 450-486",
      "cfr_citation": "21 CFR 117",
      "state_code_reference": "CA Health & Safety Code § 113700-114437",
      "enforcement_agency": "SF Department of Public Health - Environmental Health",
      "agency_contact": "Food Safety Program",
      "agency_phone": "628-652-3400",
      "agency_url": "https://www.sfdph.org/dph/EH/Food/",
      "penalty_for_violation": "Permit suspension, closure, fines up to $1,000 per day",
      "fine_amount_min": 100.00,
      "fine_amount_max": 1000.00,
      "requirements": {
        "facility_requirements": {
          "min_square_feet": null,
          "required_equipment": [
            "3-compartment sink",
            "handwashing sink",
            "commercial refrigeration",
            "approved food storage"
          ],
          "ventilation": "Type I hood required for cooking operations",
          "flooring": "Non-porous, easily cleanable surface",
          "walls": "Smooth, light-colored, easily cleanable",
          "lighting": "Minimum 50 foot-candles at food prep surfaces"
        },
        "staffing_requirements": {
          "certified_food_manager": true,
          "food_handler_certs": "all food handling staff within 7 days of hire",
          "manager_presence": "Certified food manager on-site during all hours of operation"
        },
        "operational_requirements": {
          "temperature_logs": "Required for all TCS foods",
          "cleaning_schedule": "Written cleaning and sanitizing schedule",
          "pest_control": "Licensed pest control service contract"
        }
      },
      "application_process": {
        "steps": [
          {
            "step_number": 1,
            "description": "Submit plan review application",
            "url": "https://www.sfdph.org/dph/EH/Food/Plan_Review.asp",
            "required_documents": [
              "Floor plan showing equipment layout",
              "Equipment specifications",
              "Menu",
              "Food safety procedures"
            ]
          },
          {
            "step_number": 2,
            "description": "Pay plan review fee",
            "fee": 458.00
          },
          {
            "step_number": 3,
            "description": "Schedule and pass pre-opening inspection",
            "contact": "628-652-3400",
            "typical_wait_time": "2-4 weeks"
          },
          {
            "step_number": 4,
            "description": "Receive permit",
            "notes": "Must be posted in public view"
          }
        ],
        "estimated_timeline": "4-8 weeks from plan submission to permit issuance",
        "online_application_available": true
      },
      "required_documents": [
        "Completed application form",
        "Floor plan with equipment layout",
        "Equipment specification sheets",
        "Menu",
        "Food safety plan",
        "Certified food manager certificate"
      ],
      "fees": {
        "plan_review": 458.00,
        "permit_application": 458.00,
        "annual_renewal": 458.00,
        "late_renewal_penalty": 137.00,
        "routine_inspection": 0.00,
        "reinspection": 229.00
      },
      "applicable_facility_types": [
        "commercial_kitchen",
        "ghost_kitchen",
        "restaurant",
        "catering",
        "bakery",
        "commissary"
      ],
      "employee_count_threshold": null,
      "revenue_threshold": null,
      "renewal_period_days": 365,
      "is_active": true,
      "priority": "critical",
      "data_source": "SF Department of Public Health website",
      "notes": "Risk-based inspection frequency: High Risk (3-4x/year), Medium Risk (2x/year), Low Risk (1x/year)"
    },
    {
      "regulation_type": "business_license",
      "title": "Business Registration Certificate",
      "description": "All businesses operating in San Francisco must register and pay business taxes",
      "local_code_reference": "SF Business & Tax Regulations Code Article 12",
      "enforcement_agency": "SF Office of the Treasurer & Tax Collector",
      "agency_url": "https://sftreasurer.org/business/register-your-business",
      "priority": "critical",
      "applicable_facility_types": [
        "commercial_kitchen",
        "ghost_kitchen",
        "restaurant",
        "catering",
        "food_truck",
        "bakery",
        "commissary"
      ],
      "requirements": {
        "registration_requirements": {
          "business_entity": "Must be registered with CA Secretary of State",
          "owner_id": "Valid government-issued ID",
          "business_address": "Physical address in San Francisco"
        }
      },
      "application_process": {
        "steps": [
          {
            "step_number": 1,
            "description": "Register online",
            "url": "https://www.sf.gov/register-your-business"
          },
          {
            "step_number": 2,
            "description": "Pay registration fee",
            "fee": 91.00
          }
        ],
        "estimated_timeline": "1-2 weeks"
      },
      "fees": {
        "initial_registration": 91.00,
        "annual_renewal": 91.00,
        "late_fee": 25.00
      },
      "renewal_period_days": 365,
      "is_active": true
    }
  ],
  "insurance_requirements": [
    {
      "insurance_type": "general_liability",
      "coverage_name": "Commercial General Liability Insurance",
      "description": "Coverage for third-party bodily injury and property damage claims",
      "minimum_coverage_amount": 1000000.00,
      "per_occurrence_limit": 1000000.00,
      "aggregate_limit": 2000000.00,
      "deductible_max": null,
      "applicable_facility_types": [
        "commercial_kitchen",
        "ghost_kitchen",
        "restaurant",
        "catering",
        "bakery"
      ],
      "employee_count_threshold": null,
      "local_ordinance": "SF Administrative Code § 21.40",
      "state_requirement": "CA Business & Professions Code § 19340",
      "is_mandatory": true,
      "effective_date": null,
      "notes": "Required for business license renewal. Many landlords require higher limits ($2M or more)."
    },
    {
      "insurance_type": "workers_compensation",
      "coverage_name": "Workers' Compensation Insurance",
      "description": "Coverage for employee work-related injuries and illnesses",
      "minimum_coverage_amount": 1000000.00,
      "applicable_facility_types": [
        "commercial_kitchen",
        "ghost_kitchen",
        "restaurant",
        "catering",
        "bakery"
      ],
      "employee_count_threshold": 1,
      "state_requirement": "CA Labor Code § 3700",
      "is_mandatory": true,
      "notes": "Required in California for any business with employees. Sole proprietors may opt out."
    },
    {
      "insurance_type": "product_liability",
      "coverage_name": "Product Liability Insurance",
      "description": "Coverage for claims related to food-borne illness or contamination",
      "minimum_coverage_amount": 1000000.00,
      "per_occurrence_limit": 1000000.00,
      "aggregate_limit": 2000000.00,
      "applicable_facility_types": [
        "commercial_kitchen",
        "ghost_kitchen",
        "catering",
        "bakery"
      ],
      "is_mandatory": false,
      "notes": "Not legally required but strongly recommended. Often required by distribution partners."
    }
  ]
}
```

#### How to Import:

```bash
cd /home/user/Prep

# Import the JSON file
python -c "
from apps.city_regulatory_service.etl import CityRegulatoryETL

etl = CityRegulatoryETL()
stats = etl.load_from_json('data/cities/san_francisco_ca.json')

print('Import Results:')
print(f'  Jurisdictions created: {stats[\"jurisdictions_created\"]}')
print(f'  Jurisdictions updated: {stats[\"jurisdictions_updated\"]}')
print(f'  Regulations created: {stats[\"regulations_created\"]}')
print(f'  Regulations updated: {stats[\"regulations_updated\"]}')
print(f'  Insurance requirements created: {stats[\"insurance_requirements_created\"]}')
print(f'  Errors: {len(stats[\"errors\"])}')

if stats['errors']:
    print('\\nErrors:')
    for error in stats['errors']:
        print(f'  - {error}')

etl.close()
"
```

---

### Method 2: CSV Files

**Best for:** Tabular data from spreadsheets

#### File 1: `{city}_regulations.csv`

```csv
regulation_type,title,description,local_code_reference,enforcement_agency,priority,applicable_facility_types,fees,renewal_period_days,is_active
health_permit,"Food Service Establishment Permit","Required permit for all food service operations","SF Health Code § 450-486","SF Department of Public Health",critical,"commercial_kitchen|ghost_kitchen|restaurant","{\"application_fee\": 458.00, \"annual_renewal\": 458.00}",365,true
business_license,"Business Registration Certificate","All businesses must register","SF B&T Code Article 12","SF Treasurer & Tax Collector",critical,"commercial_kitchen|ghost_kitchen|restaurant|catering","{\"initial_registration\": 91.00, \"annual_renewal\": 91.00}",365,true
```

#### File 2: `{city}_insurance.csv`

```csv
insurance_type,coverage_name,minimum_coverage_amount,applicable_facility_types,is_mandatory
general_liability,"Commercial General Liability",1000000.00,"commercial_kitchen|ghost_kitchen|restaurant",true
workers_compensation,"Workers Compensation",1000000.00,"commercial_kitchen|ghost_kitchen|restaurant",true
product_liability,"Product Liability",1000000.00,"commercial_kitchen|ghost_kitchen",false
```

#### How to Import:

```bash
python -c "
from apps.city_regulatory_service.etl import CityRegulatoryETL

etl = CityRegulatoryETL()
stats = etl.load_from_csv(
    city_name='San Francisco',
    state='CA',
    regulations_csv='data/cities/san_francisco_regulations.csv',
    insurance_csv='data/cities/san_francisco_insurance.csv'
)

print(f'Imported {stats[\"regulations_created\"]} regulations')
print(f'Imported {stats[\"insurance_requirements_created\"]} insurance requirements')

etl.close()
"
```

---

### Method 3: API Upload

**Best for:** Programmatic access, CI/CD pipelines

```bash
curl -X POST http://localhost:8002/city/data/ingest \
  -H "Content-Type: application/json" \
  -d @data/cities/san_francisco_ca.json
```

Response:
```json
{
  "success": true,
  "city_id": "abc-123",
  "regulations_imported": 15,
  "insurance_requirements_imported": 3,
  "errors": null,
  "warnings": null,
  "import_timestamp": "2024-11-01T00:00:00Z"
}
```

---

## Field Mappings & Requirements

### Required Fields

#### Regulations
- ✅ `regulation_type` (enum: health_permit, business_license, fire_safety, etc.)
- ✅ `title`
- ✅ `enforcement_agency`
- ✅ `applicable_facility_types` (array)
- ✅ `priority` (critical, high, medium, low)
- ✅ `is_active` (true/false)

#### Insurance
- ✅ `insurance_type`
- ✅ `coverage_name`
- ✅ `minimum_coverage_amount` (float, USD)
- ✅ `applicable_facility_types` (array)
- ✅ `is_mandatory` (true/false)

### Optional But Recommended

- `description`: Detailed explanation
- `local_code_reference`: City ordinance/code citation
- `cfr_citation`: Link to federal requirement (e.g., "21 CFR 117")
- `fees`: Fee structure (JSON object)
- `requirements`: Detailed requirements (JSON object)
- `application_process`: Step-by-step process (JSON object)
- `renewal_period_days`: How often renewal is needed
- `notes`: Additional context

---

## Facility Types

Use these values for `applicable_facility_types`:

- `commercial_kitchen` - Full commercial kitchen
- `ghost_kitchen` - Cloud/ghost kitchen (delivery only)
- `restaurant` - Dine-in restaurant
- `catering` - Catering operation
- `food_truck` - Mobile food service
- `bakery` - Bakery
- `commissary` - Commissary kitchen
- `prep_kitchen` - Prep-only kitchen

---

## Regulation Types

Use these values for `regulation_type`:

- `health_permit` - Health department permit
- `business_license` - General business license
- `food_handler_certification` - Food handler cert requirement
- `fire_safety` - Fire safety inspection/permit
- `building_permit` - Building/construction permits
- `zoning` - Zoning compliance
- `insurance` - Insurance requirements
- `workers_compensation` - Workers comp requirement
- `grease_trap` - Grease trap requirements
- `waste_management` - Waste/recycling requirements
- `alcohol_license` - Alcohol service license (if applicable)

---

## Insurance Types

Use these values for `insurance_type`:

- `general_liability` - Commercial general liability
- `workers_compensation` - Workers compensation
- `product_liability` - Product liability
- `property_insurance` - Property insurance
- `business_interruption` - Business interruption
- `umbrella_policy` - Umbrella/excess liability

---

## Example: Complete NYC Import

```json
{
  "city_info": {
    "city_name": "New York",
    "state": "NY",
    "county": "New York County",
    "fips_code": "36061",
    "population": 8336817,
    "health_department_name": "NYC Department of Health and Mental Hygiene",
    "health_department_url": "https://www.nyc.gov/site/doh/index.page",
    "business_licensing_dept": "NYC Department of Consumer and Worker Protection",
    "business_licensing_url": "https://www.nyc.gov/site/dca/index.page",
    "fire_department_name": "FDNY Fire Prevention",
    "fire_department_url": "https://www.nyc.gov/site/fdny/index.page",
    "phone": "311",
    "timezone": "America/New_York"
  },
  "regulations": [
    {
      "regulation_type": "health_permit",
      "title": "Food Service Establishment Permit",
      "description": "Required for all food service establishments in NYC",
      "local_code_reference": "NYC Health Code Article 81",
      "cfr_citation": "21 CFR 117",
      "enforcement_agency": "NYC DOHMH",
      "agency_url": "https://www1.nyc.gov/site/doh/business/food-operators/food-service-establishment-permits.page",
      "priority": "critical",
      "applicable_facility_types": [
        "commercial_kitchen",
        "ghost_kitchen",
        "restaurant",
        "catering"
      ],
      "fees": {
        "initial_permit": 280.00,
        "2_year_renewal": 560.00,
        "inspection_fee": 0
      },
      "renewal_period_days": 730,
      "is_active": true,
      "requirements": {
        "facility_requirements": {
          "required_equipment": [
            "3-compartment sink",
            "handwashing sinks",
            "commercial refrigeration"
          ]
        },
        "staffing_requirements": {
          "food_protection_certificate": "At least one supervisor per shift"
        }
      }
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
        "ghost_kitchen",
        "restaurant"
      ],
      "is_mandatory": true
    }
  ]
}
```

Save as `data/cities/new_york_ny.json` and import:

```bash
python -c "
from apps.city_regulatory_service.etl import CityRegulatoryETL
etl = CityRegulatoryETL()
stats = etl.load_from_json('data/cities/new_york_ny.json')
print(f'NYC data imported: {stats[\"regulations_created\"]} regulations')
etl.close()
"
```

---

## Verification After Import

### 1. Check via API

```bash
# List all regulations for the city
curl "http://localhost:8002/city/San%20Francisco/CA/regulations"

# Get summary statistics
curl "http://localhost:8002/city/San%20Francisco/CA/regulations/summary"

# Get insurance requirements
curl "http://localhost:8002/city/San%20Francisco/CA/insurance-requirements"
```

### 2. Check via Database

```bash
sqlite3 data/cities/prep_city_regulations.sqlite

# Count regulations by city
SELECT c.city_name, c.state, COUNT(*) as reg_count
FROM city_regulations r
JOIN city_jurisdictions c ON r.city_id = c.id
GROUP BY c.city_name, c.state;

# View regulations for a city
SELECT regulation_type, title, priority
FROM city_regulations r
JOIN city_jurisdictions c ON r.city_id = c.id
WHERE c.city_name = 'San Francisco' AND c.state = 'CA';
```

---

## Updating Existing Data

### Full Re-Import
Re-running the import will update existing records:

```bash
python -c "
from apps.city_regulatory_service.etl import CityRegulatoryETL
etl = CityRegulatoryETL()
stats = etl.load_from_json('data/cities/san_francisco_ca.json')
print(f'Updated: {stats[\"regulations_updated\"]} regulations')
etl.close()
"
```

### Partial Updates via API

```bash
curl -X POST http://localhost:8002/city/data/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "city_name": "San Francisco",
    "state": "CA",
    "data_source": "Fee update 2024",
    "verification_date": "2024-11-01T00:00:00Z",
    "regulations": [
      {
        "regulation_type": "health_permit",
        "title": "Food Service Establishment Permit",
        "fees": {
          "application_fee": 475.00,
          "annual_renewal": 475.00
        }
      }
    ]
  }'
```

---

## For Your Team

### Suggested Workflow

1. **Collect Data** for one city (start with your local city for easy verification)

2. **Create JSON File** using the template above
   - Save as `data/cities/{city_name}_{state}.json`

3. **Import and Test**
   ```bash
   python -c "
   from apps.city_regulatory_service.etl import CityRegulatoryETL
   etl = CityRegulatoryETL()
   stats = etl.load_from_json('data/cities/your_file.json')
   print(stats)
   etl.close()
   "
   ```

4. **Verify via API**
   ```bash
   curl "http://localhost:8002/city/Your%20City/ST/regulations"
   ```

5. **Test Compliance Check**
   ```bash
   curl -X POST http://localhost:8002/city/Your%20City/ST/compliance-check \
     -H "Content-Type: application/json" \
     -d @test_facility.json
   ```

6. **Repeat for all 8 cities**

7. **Export for Review** (optional)
   ```bash
   python -c "
   from apps.city_regulatory_service.etl import CityRegulatoryETL
   etl = CityRegulatoryETL()
   etl.export_city_data_to_json(
       'San Francisco',
       'CA',
       'data/cities/sf_export.json'
   )
   etl.close()
   "
   ```

---

## Support

If you encounter issues:

1. **Check logs** - ETL reports errors and warnings
2. **Validate JSON** - Use https://jsonlint.com/
3. **Check field types** - Ensure numbers are numbers, not strings
4. **Verify enums** - Use exact values for regulation_type, facility_type, etc.

The ETL pipeline will report:
- ✅ Records created
- ✅ Records updated
- ⚠️ Warnings (e.g., unknown regulation types)
- ❌ Errors (e.g., missing required fields)

---

Ready to ingest your collected data! 🚀
