# Federal Regulatory Service

**Federal compliance backbone for the Prep Regulatory Engine**

This microservice provides API access to FDA-recognized accreditation bodies, certification bodies, and food safety scopes under FSMA (Food Safety Modernization Act).

## Overview

The Federal Regulatory Service establishes the authority chain from federal oversight down to on-the-ground certification:

```
[FDA/FSMA Program Scope]
   ↓
[Accreditation Body (ANAB / IAS)]
   ↓
[Certification Body (3rd Party Auditor)]
   ↓
[Facility / Kitchen Operator]
```

## Features

- **Scope Catalog**: List all FDA/FSMA food safety program scopes with CFR citations
- **Certifier Discovery**: Find authorized certification bodies by scope
- **Expiration Monitoring**: Track certifications expiring within specified timeframes
- **Authority Chain Validation**: Verify complete certification legitimacy from FDA to facility
- **Activity Matching**: Match kitchen activities to required certifiers and scopes
- **ETL Pipeline**: Automated data refresh from ANAB/IAS directories

## Installation

```bash
cd apps/federal_regulatory_service
pip install -r requirements.txt
```

## Running the Service

```bash
# Development mode
python main.py

# Production mode with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4
```

## API Endpoints

### Core Endpoints

**GET /healthz**
- Health check with database status and record counts

**GET /federal/scopes**
- List all available food safety scopes with CFR anchors

**GET /federal/accreditation-bodies**
- List FDA-recognized accreditation bodies (ANAB, IAS)

**GET /federal/certification-bodies**
- List certification bodies, optionally filtered by scope
- Query params: `scope` (optional)

**GET /federal/certifiers**
- List certifiers with full details including accreditation lineage
- Query params:
  - `scope` (optional): Filter by scope name
  - `active_only` (default: true): Only return active certifications
  - `expiring_within_days` (optional): Filter to expiring certifications

**GET /federal/certifiers/{certifier_id}**
- Get detailed information about a specific certification body

**GET /federal/expiring**
- Get certifications expiring within specified days
- Query params: `days` (default: 180, range: 1-730)

**GET /federal/authority-chain**
- Get complete authority chain for certification validation
- Query params:
  - `certifier_name` (required)
  - `scope_name` (required)

**POST /federal/match**
- Match certifiers based on activity type and jurisdiction
- Request body:
  ```json
  {
    "activity": "seafood_haccp",
    "jurisdiction": "CA-Los Angeles"
  }
  ```

## Example Requests

### Find certifiers for Preventive Controls for Human Food

```bash
curl "http://localhost:8001/federal/certifiers?scope=Human%20Food"
```

### Check upcoming expirations (next 90 days)

```bash
curl "http://localhost:8001/federal/expiring?days=90"
```

### Match certifiers for produce safety

```bash
curl -X POST "http://localhost:8001/federal/match" \
  -H "Content-Type: application/json" \
  -d '{"activity": "produce_safety", "jurisdiction": "CA-Los Angeles"}'
```

### Validate authority chain

```bash
curl "http://localhost:8001/federal/authority-chain?certifier_name=NSF&scope_name=Human%20Food"
```

## ETL Pipeline

The service includes an ETL pipeline for refreshing federal compliance data from upstream sources.

### Run ETL Manually

```bash
python etl.py
```

### ETL Process

1. **Extract**: Read from CSV files or fetch from ANAB/IAS APIs
2. **Transform**: Normalize and validate data
3. **Load**: Update SQLite database
4. **Validate**: Check expiration dates and update statuses

### Scheduled Execution

For production, configure a cron job or scheduler:

```cron
# Run ETL weekly on Sundays at 2 AM
0 2 * * 0 /usr/bin/python /path/to/apps/federal_regulatory_service/etl.py
```

## Data Dictionary

See `/data/federal/prep_federal_layer_data_dictionary.md` for complete data model documentation.

## Database Schema

The service uses SQLite with four core tables:

- **accreditation_bodies**: FDA-recognized ABs (ANAB, IAS)
- **certification_bodies**: Third-party auditors
- **scopes**: Food safety program areas (PCHF, PCAF, Produce, etc.)
- **ab_cb_scope_links**: Relationships with validity dates

## Integration

### With Compliance Service

The Federal Regulatory Service integrates with the main compliance service:

```python
import httpx

async def check_certifier_validity(certifier_name: str, scope: str) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://federal-regulatory-service:8001/federal/authority-chain",
            params={"certifier_name": certifier_name, "scope_name": scope}
        )
        data = response.json()
        return data["chain_validity"] == "VALID"
```

### With Graph Service

For graph-based reasoning:

```python
# Transform to graph nodes and edges
nodes = [
    {"type": "AccreditationBody", "id": ab_id, ...},
    {"type": "CertificationBody", "id": cb_id, ...},
    {"type": "Scope", "id": scope_id, ...}
]

edges = [
    {"from": ab_id, "to": cb_id, "type": "ACCREDITS", "since": date, "until": date},
    {"from": cb_id, "to": scope_id, "type": "AUTHORIZED_FOR", ...}
]
```

## Development

### Project Structure

```
apps/federal_regulatory_service/
├── __init__.py              # Package init
├── main.py                  # FastAPI application
├── etl.py                   # ETL pipeline
├── requirements.txt         # Python dependencies
├── README.md               # This file
└── tests/
    ├── __init__.py
    └── test_service.py     # Integration tests
```

### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

## Monitoring

### Health Check

```bash
curl http://localhost:8001/healthz
```

### Metrics to Monitor

- Database connection status
- Record counts per table
- Expiring certifications count
- API response times
- ETL run success/failure rates

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Environment Variables

- `DATABASE_PATH`: Path to SQLite database (default: auto-detected)
- `LOG_LEVEL`: Logging level (default: INFO)
- `HOST`: Service host (default: 0.0.0.0)
- `PORT`: Service port (default: 8001)

## Support

For issues or questions:
- Technical issues: See repository documentation
- Data accuracy: Refer to FDA's official Third-Party Certification Program
- Regulatory interpretation: Consult FDA guidance or legal counsel

## Version

Current version: **1.0.0**

## License

See main repository LICENSE file.
