# City Regulatory Service

City-level regulatory ingestion and compliance API for Prep's Regulatory Engine.

## Overview

The City Regulatory Service extends Prep's federal regulatory engine to support city-level compliance requirements. It provides:

- **City-specific ingestion adapters** for extracting regulatory data from diverse municipal sources
- **Normalization layer** with shared jurisdictional ontology and requirement taxonomy
- **RESTful API** for querying city compliance requirements
- **ETL orchestrator** for automated data ingestion and updates

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│             City Regulatory Service (Port 8002)         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────┐ │
│  │   Ingestion  │→→→│ Normalization│→→→│  Database  │ │
│  │   Adapters   │   │    Layer     │   │   Models   │ │
│  └──────────────┘   └──────────────┘   └────────────┘ │
│         ↓                   ↓                  ↓       │
│  ┌──────────────────────────────────────────────────┐ │
│  │              FastAPI Endpoints                   │ │
│  │   - /compliance/requirements                     │ │
│  │   - /compliance/query                            │ │
│  │   - /cities/jurisdictions                        │ │
│  │   - /etl/run                                     │ │
│  └──────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                         ↕
┌─────────────────────────────────────────────────────────┐
│       Federal Regulatory Service (Port 8001)            │
│       Compliance Service                                │
└─────────────────────────────────────────────────────────┘
```

## Currently Supported Cities

- **San Francisco, CA**
- **New York, NY**

## Database Schema

### Core Tables

#### `city_jurisdictions`
- City metadata and portal URLs
- Food code adoption info
- Demographics

#### `city_agencies`
- Government agencies enforcing regulations
- Contact information
- Portal links

#### `city_requirements`
- Normalized regulatory requirements
- Applicability rules (business types)
- Required documents
- Fee structures
- Renewal frequencies
- Inspection requirements

#### `city_requirement_links`
- Links city requirements to federal scopes
- Relationship types (inherits, extends, overrides)

#### `city_etl_runs`
- ETL run tracking
- Success/failure metrics
- Error logs

## API Endpoints

### Health Check

```bash
GET /healthz
```

Returns service status and available cities.

### List Jurisdictions

```bash
GET /cities/jurisdictions
```

Returns all available city jurisdictions with metadata.

### List Agencies

```bash
GET /cities/{city}/agencies
```

Returns agencies for a specific city.

### Query Requirements

```bash
GET /compliance/requirements?jurisdiction=San Francisco&business_type=restaurant
```

Query compliance requirements with filters:
- `jurisdiction` - City name
- `business_type` - Business type (restaurant, food_truck, etc.)
- `requirement_type` - Requirement category

### Compliance Query

```bash
POST /compliance/query
Content-Type: application/json

{
  "jurisdiction": "San Francisco",
  "business_type": "restaurant",
  "requirement_type": "health_permit"
}
```

Returns comprehensive compliance checklist with cost estimates.

### Get Requirement Detail

```bash
GET /compliance/requirements/{requirement_id}
```

Returns detailed requirement information with jurisdiction and agency data.

### Trigger ETL

```bash
POST /etl/run
Content-Type: application/json

{
  "city": "San Francisco"
}
```

Triggers ingestion pipeline for specified city (or all cities if null).

## Running the Service

### Prerequisites

- Python 3.10+
- PostgreSQL (or SQLite for development)
- Dependencies: `pip install -r requirements.txt`

### Start the service

```bash
# Set database URL
export DATABASE_URL="postgresql://user:pass@localhost/prep"

# Run database migrations
python -m prep.models.db init_db

# Start the service
python -m apps.city_regulatory_service.main
```

Service runs on `http://localhost:8002`

### Run ETL to populate data

```bash
curl -X POST http://localhost:8002/etl/run \
  -H "Content-Type: application/json" \
  -d '{"city": null}'
```

## Adding New Cities

To add support for a new city:

1. **Create adapter** in `src/adapters/{city}_adapter.py`:

```python
class BostonAdapter:
    CITY_NAME = "Boston"
    STATE = "MA"

    @classmethod
    def get_all_requirements(cls) -> list[dict[str, Any]]:
        # Extract and return requirements
        pass
```

2. **Register adapter** in `src/etl/orchestrator.py`:

```python
CITY_ADAPTERS = {
    "San Francisco": SanFranciscoAdapter,
    "New York": NewYorkCityAdapter,
    "Boston": BostonAdapter,  # Add here
}
```

3. **Run ETL**:

```bash
curl -X POST http://localhost:8002/etl/run \
  -d '{"city": "Boston"}'
```

## Normalization Layer

The normalization layer standardizes diverse city regulatory data using:

### Requirement Type Taxonomy

- `business_license` - General business registration
- `restaurant_license` - Food service permits
- `food_safety_training` - Manager certifications
- `health_permit` - Health department permits
- `insurance` - Liability coverage
- `inspection` - Inspection requirements
- `zoning` - Zoning approvals
- `building` - Building permits
- `fire_safety` - Fire permits

### Renewal Frequencies

- `annual` - Yearly renewal
- `biannual` - Every 6 months
- `triennial` - Every 3 years
- `on_event` - Event-triggered
- `perpetual` - No renewal needed

### Submission Channels

- `online` - Web portal
- `mail` - Postal submission
- `in_person` - Walk-in counter
- `hybrid` - Multiple options

## Integration with Federal Layer

City requirements can be linked to federal scopes via `city_requirement_links`:

- **inherits** - City requirement inherits from federal scope
- **extends** - City adds additional requirements
- **overrides** - City has stricter requirements

Example:
- SF Food Manager Cert → Federal "Preventive Controls for Human Food" (inherits)
- NYC Food Protection Certificate → Federal PCHF (extends, adds NYC-specific exam)

## Maintenance

### Update City Data

Run ETL periodically to refresh city requirements:

```bash
# Daily cron job
0 2 * * * curl -X POST http://localhost:8002/etl/run
```

### Monitor ETL Runs

Check `city_etl_runs` table for:
- Run status
- Processing statistics
- Error logs

## Testing

```bash
# Run tests
pytest apps/city_regulatory_service/tests/

# Test specific module
pytest apps/city_regulatory_service/tests/test_normalizer.py
```

## Contributing

When adding new cities or updating requirements:

1. Verify source URLs are current
2. Test normalization output
3. Run ETL and verify database records
4. Update this README with new cities

## Support

For questions or issues, contact the Prep Regulatory Engine team.
