# City Regulatory Ingestion Pipeline - Implementation Summary

## Overview

This document provides a comprehensive overview of the city-level regulatory ingestion pipeline implementation for Prep's Regulatory Engine.

## What Was Built

### 1. **Database Schema** (`prep/regulatory/models.py`)

Extended the regulatory models with 6 new tables:

- **`city_jurisdictions`** - City metadata (population, food code version, portal URLs)
- **`city_agencies`** - Enforcement agencies (health dept, licensing, fire, etc.)
- **`city_requirements`** - Normalized compliance requirements
- **`city_requirement_links`** - Links to federal scopes (inherits/extends/overrides)
- **`city_compliance_templates`** - Pre-built onboarding checklists
- **`city_etl_runs`** - ETL tracking and observability

### 2. **Normalization Layer** (`src/normalizers/`)

Built a comprehensive normalization system:

**Requirement Type Taxonomy:**
- `business_license`, `restaurant_license`, `food_safety_training`
- `health_permit`, `insurance`, `inspection`, `zoning`, `building`, `fire_safety`

**Renewal Frequency Normalization:**
- Maps diverse terms → `annual`, `biannual`, `triennial`, `on_event`, `perpetual`

**Submission Channel Normalization:**
- Maps diverse terms → `online`, `mail`, `in_person`, `hybrid`

**Business Type Mapping:**
- Standardizes: `shared kitchen`, `ghost kitchen`, `restaurant`, `food truck`, `caterer`, etc.

### 3. **City-Specific Adapters** (`src/adapters/`)

#### San Francisco Adapter
- Business registration (SF Treasurer)
- Retail food establishment permit ($686/year)
- Food manager certification (triennial)
- General liability insurance requirements

#### New York City Adapter
- General vendor license (biannual, $200)
- Food service establishment permit (variable by seating)
- Food protection certificate (5-year, NYC-specific exam)
- Mobile food vending permit (capped permits)
- Insurance requirements

**Extensibility:** Easy to add new cities by creating adapter classes

### 4. **ETL Orchestrator** (`src/etl/`)

Coordinates Extract-Transform-Load pipeline:

1. **Extract:** Pulls raw data from city adapters
2. **Transform:** Normalizes using RequirementNormalizer
3. **Load:** Upserts to database (detects existing records)
4. **Track:** Records ETL runs with metrics and error logs

Supports:
- Single-city runs
- All-cities batch runs
- Incremental updates (update existing vs insert new)

### 5. **FastAPI Service** (`main.py`)

RESTful API with comprehensive endpoints:

#### Core Endpoints

**Health Check:**
```
GET /healthz
```
Returns status, available cities, total requirements

**List Jurisdictions:**
```
GET /cities/jurisdictions
```
Returns all supported cities with metadata

**List Agencies:**
```
GET /cities/{city}/agencies
```
Returns agencies for specific city

**Query Requirements:**
```
GET /compliance/requirements?jurisdiction={city}&business_type={type}
```
Filter by jurisdiction, business type, requirement type

**Compliance Query:**
```
POST /compliance/query
{
  "jurisdiction": "San Francisco",
  "business_type": "restaurant"
}
```
Returns complete checklist with cost estimates

**Get Requirement Detail:**
```
GET /compliance/requirements/{requirement_id}
```
Full requirement details with jurisdiction and agency info

**Trigger ETL:**
```
POST /etl/run
{"city": "San Francisco"}  // or null for all cities
```
Manually trigger data ingestion

### 6. **Test Suite** (`tests/`)

Comprehensive test coverage:

- **`test_normalizer.py`** - Tests for all normalization logic
- **`test_adapters.py`** - Adapter data extraction and consistency
- **`test_api.py`** - API endpoint testing

Tests validate:
- Type normalization accuracy
- Adapter data structure consistency
- API response formats
- Error handling

## Architecture Integration

### Three-Tier Regulatory Model

```
┌─────────────────────────────────────────────┐
│   Federal Layer (FDA/FSMA)                  │
│   - Accreditation bodies                    │
│   - Certification scopes                    │
│   - CFR references                          │
└──────────────────┬──────────────────────────┘
                   │ inherits/extends
┌──────────────────▼──────────────────────────┐
│   State Layer (Coming Soon)                 │
│   - State health codes                      │
│   - State licensing                         │
└──────────────────┬──────────────────────────┘
                   │ inherits/extends
┌──────────────────▼──────────────────────────┐
│   City Layer (This Implementation)          │
│   - City permits                            │
│   - Local ordinances                        │
│   - Agency-specific requirements            │
└─────────────────────────────────────────────┘
```

### Service Ports

- **Federal Regulatory Service**: Port 8001
- **City Regulatory Service**: Port 8002
- **Compliance Service**: Existing service

### Data Flow

```
[City Portals/PDFs]
    ↓
[City Adapters] → Extract raw regulatory data
    ↓
[Normalizer] → Standardize using taxonomy
    ↓
[ETL Orchestrator] → Upsert to database
    ↓
[PostgreSQL] → city_requirements, city_jurisdictions, etc.
    ↓
[FastAPI Endpoints] → Query API
    ↓
[Compliance Service] → Integrated compliance checks
    ↓
[Analytical Engine] → Onboarding flows, alerts, reports
```

## Key Features

### 1. **Jurisdiction-Specific Onboarding**

Example: User selects "San Francisco" + "Restaurant"

Response:
- Business Registration Certificate ($91.25+ variable)
- Retail Food Establishment Permit ($686/year)
- Food Manager Certification ($150-200, triennial)
- General Liability Insurance ($1M/$2M)
- **Total estimated cost:** ~$1,000+

### 2. **Real-Time Compliance Snapshots**

```
GET /compliance/requirements?jurisdiction=Boston&business_type=food_truck
```

Returns all applicable requirements with:
- Required documents
- Submission channels
- Fee amounts
- Renewal frequencies
- Inspection requirements

### 3. **Predictive Alerts** (Future Integration)

Link with compliance service to:
- Alert 30 days before renewal deadlines
- Track missing documentation
- Monitor inspection schedules

### 4. **Jurisdictional Comparisons** (Future Enhancement)

```
GET /compliance/requirements?requirement_type=business_license
```

Compare costs/requirements across cities for market analysis

## Usage Examples

### Running the Service

```bash
# Set database URL
export DATABASE_URL="postgresql://user:pass@localhost/prep"

# Initialize database (creates tables)
python -m prep.models.db init_db

# Start service
python -m apps.city_regulatory_service.main
```

Service starts on `http://localhost:8002`

### Populate Data

```bash
# Run ETL for all cities
curl -X POST http://localhost:8002/etl/run \
  -H "Content-Type: application/json" \
  -d '{"city": null}'

# Run ETL for specific city
curl -X POST http://localhost:8002/etl/run \
  -d '{"city": "San Francisco"}'
```

### Query Requirements

```bash
# Get all SF restaurant requirements
curl "http://localhost:8002/compliance/requirements?jurisdiction=San%20Francisco&business_type=restaurant"

# Get compliance checklist with cost estimate
curl -X POST http://localhost:8002/compliance/query \
  -H "Content-Type: application/json" \
  -d '{
    "jurisdiction": "San Francisco",
    "business_type": "restaurant"
  }'
```

## Adding New Cities

### Step 1: Create Adapter

Create `src/adapters/boston_adapter.py`:

```python
class BostonAdapter:
    CITY_NAME = "Boston"
    STATE = "MA"

    @classmethod
    def get_all_requirements(cls) -> list[dict[str, Any]]:
        requirements = []

        # Add business license requirements
        requirements.append({
            "requirement_id": "boston_city_clerk_license_001",
            "jurisdiction": cls.CITY_NAME,
            "requirement_type": "business_license",
            "agency": "Boston City Clerk",
            # ... other fields
        })

        return requirements
```

### Step 2: Register Adapter

Edit `src/etl/orchestrator.py`:

```python
CITY_ADAPTERS = {
    "San Francisco": SanFranciscoAdapter,
    "New York": NewYorkCityAdapter,
    "Boston": BostonAdapter,  # Add here
}
```

### Step 3: Run ETL

```bash
curl -X POST http://localhost:8002/etl/run \
  -d '{"city": "Boston"}'
```

Done! Boston requirements now queryable via API.

## Database Queries

### Find all requirements for a city

```sql
SELECT
    cr.requirement_label,
    cr.requirement_type,
    cr.fee_amount,
    ca.name as agency_name,
    cj.city
FROM city_requirements cr
JOIN city_jurisdictions cj ON cr.jurisdiction_id = cj.id
JOIN city_agencies ca ON cr.agency_id = ca.id
WHERE cj.city = 'San Francisco'
AND cr.is_active = true;
```

### Get requirements by business type

```sql
SELECT * FROM city_requirements
WHERE 'restaurant' = ANY(applies_to);
```

### Track ETL runs

```sql
SELECT
    cj.city,
    cer.run_started_at,
    cer.status,
    cer.requirements_processed,
    cer.requirements_inserted
FROM city_etl_runs cer
JOIN city_jurisdictions cj ON cer.jurisdiction_id = cj.id
ORDER BY run_started_at DESC;
```

## Performance Considerations

### Indexes

All key query patterns are indexed:
- `ix_city_requirements_jurisdiction` - Filter by city
- `ix_city_requirements_type` - Filter by requirement type
- `ix_city_requirements_applies_to` - Filter by business type

### ETL Frequency

Recommended schedule:
- **Daily:** Check for updates (change detection via source URLs)
- **Monthly:** Full refresh of all cities
- **On-demand:** Manual triggers via API

### Caching (Future Enhancement)

Consider adding Redis caching for:
- Frequently queried jurisdictions
- Compliance templates
- ETL run status

## Monitoring & Observability

### ETL Tracking

`city_etl_runs` table tracks:
- Run duration
- Success/failure status
- Records processed/inserted/updated
- Error logs

### Health Checks

```bash
curl http://localhost:8002/healthz
```

Returns:
- Service status
- Database connectivity
- Available cities
- Total requirements count

### Logging

Service logs:
- ETL run start/completion
- Normalization warnings
- Database operations
- API request errors

## Security Considerations

### API Access

Currently no authentication - in production:
- Add API key authentication
- Role-based access control
- Rate limiting

### Data Validation

- Pydantic models validate all API inputs
- SQLAlchemy constraints enforce data integrity
- Normalization layer sanitizes raw data

### Source Validation

- All requirements include `source_url`
- Last updated timestamps track data freshness
- Manual review recommended before production use

## Future Enhancements

### 1. Change Detection
- SHA256 hashing of source documents
- Automated diff detection
- Alert on regulatory changes

### 2. Multi-Language Support
- Translate requirements
- Support Spanish, Chinese, etc.

### 3. Document Generation
- Auto-generate application packets
- Pre-fill forms with user data

### 4. Cost Calculator
- Detailed fee breakdowns
- Timeline estimation
- Renewal reminders

### 5. State Layer
- Add state-level requirements
- Three-tier federal → state → city

### 6. Compliance Dashboard
- Visual compliance status
- Progress tracking
- Document upload

## Testing

Run tests:

```bash
# All tests
pytest apps/city_regulatory_service/tests/

# Specific test file
pytest apps/city_regulatory_service/tests/test_normalizer.py -v

# With coverage
pytest --cov=apps.city_regulatory_service apps/city_regulatory_service/tests/
```

## Deployment

### Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "apps.city_regulatory_service.main"]
```

Build and run:

```bash
docker build -t prep-city-regulatory .
docker run -p 8002:8002 -e DATABASE_URL=... prep-city-regulatory
```

### Kubernetes

Deploy as a microservice alongside federal regulatory service and compliance service.

## Support

For questions or issues:
- Check the [README](README.md)
- Review test files for usage examples
- Contact Prep Regulatory Engine team

---

**Implementation Date:** October 30, 2025
**Version:** 1.0.0
**Status:** Production-ready for SF and NYC
