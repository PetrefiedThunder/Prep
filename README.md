# Prep

## Overview
Prep is a streamlined compliance and marketplace platform for commercial kitchen
sharing. The project has been trimmed down to focus on the production-ready
flows that hosts and renters rely on today: verifying regulatory standing,
booking kitchens, and getting paid.

## Current Scope
- **Federal Regulatory Service** (`apps/federal_regulatory_service`) tracks FDA
  accreditation and certification relationships.
- **City Regulatory Service** (`apps/city_regulatory_service`) layers in
  municipal permit rules for eight major U.S. cities.
- **Compliance Service** (`apps/compliance_service`) automates document checks,
  OCR processing, and follow-up guidance.
- **Booking Service** (`apps/bookings`) manages atomic reservations and
  availability holds.
- **Payments Pipeline** (`prep/payments`) integrates with Stripe for charges,
  refunds, platform fees, and payouts.
- **API Gateway** (`apps/api_gateway`) orchestrates the core backend flows and
  exposes an OpenAPI-described surface area.
- **HarborHomes Frontend** (`apps/harborhomes`) delivers the React/Next.js
  marketplace experience used for demos and manual QA.

## Architecture Highlights
- **Runtime stack:** Python (FastAPI), Node.js (Express/Fastify), and React.
- **Data stores:** PostgreSQL for operational data, Redis for caching, and MinIO
  for document storage. Regulatory reference datasets continue to ship as
  SQLite files while the migration path to PostgreSQL is finalised.
- **Messaging:** Direct service calls – Kafka has been removed from the default
  footprint.
- **Infrastructure:** Docker Compose for local development with optional Helm
  charts under `infra/helm` for higher environments.

## Service Directory Map
- `apps/api_gateway/` – Lightweight FastAPI gateway that links bookings,
  compliance checks, and payments.
- `apps/bookings/` – Domain logic for reservations, hold workers, and
  concurrency safety helpers.
- `apps/city_regulatory_service/` – City data ETL, SQLite-backed lookups, and
  FastAPI endpoints.
- `apps/compliance_service/` – Validation of uploaded certificates and food
  safety records plus OCR helpers.
- `apps/federal_regulatory_service/` – FDA accreditation ingestion, expiry
  monitoring, and authority-chain validation.
- `apps/harborhomes/` – Next.js marketplace frontend (single frontend kept in
  the repo).
- `apps/pricing/` – Fee calculation helpers used by the payments pipeline.
- `prep/` – Shared Python libraries (bookings, compliance, payments, utilities).
- `prepchef/` – Node.js backend that powers host onboarding and booking APIs.
- `tests/` – Unit, integration, and E2E suites covering the active services.

## Documentation
Essential references live at the root of the repository:
- [`DEVELOPER_ONBOARDING.md`](DEVELOPER_ONBOARDING.md) – Environment setup and
  troubleshooting.
- [`RUNBOOK.md`](RUNBOOK.md) – Operational procedures and incident guidance.
- [`SECURITY.md`](SECURITY.md) – Security policies and reporting process.
- [`PRIVACY.md`](PRIVACY.md) – Data handling guidelines.

## Deployment
The API gateway is deployed in a containerized environment. Hosting platforms
should import the ASGI application via either `main:app` or `run_api:app`, both
of which call `api.index.create_app()` under the hood. Example launch commands
include `uvicorn main:app` for local testing or `gunicorn run_api:app` for
process-managed environments.

## Development Environment
### Docker Compose (recommended)
Start the full stack with a single command:

```bash
docker-compose up -d
```

This launches PostgreSQL, Redis, MinIO, the API gateway, compliance services,
and the HarborHomes frontend.

### Local setup
1. **Clone and install Python dependencies**
   ```bash
   git clone <repo>
   cd Prep
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```
2. **Install Node packages**
   ```bash
   cd prepchef
   npm install
   cd apps/harborhomes
   npm install
   cd ../..
   ```
3. **Configure environment**
   ```bash
   cp .env.example .env
   # Update database, Redis, MinIO, and Stripe credentials as needed
   ```
4. **Run migrations**
   ```bash
   psql $DATABASE_URL < migrations/init.sql
   for file in migrations/00*.sql; do
     [ "$(basename "$file")" = "init.sql" ] && continue
     psql $DATABASE_URL < "$file"
   done
   ```
5. **Start services**
   ```bash
   # Python compliance + regulatory APIs
   uvicorn apps.federal_regulatory_service.main:app --reload --port 8000
   uvicorn apps.city_regulatory_service.main:app --reload --port 8001
   uvicorn apps.compliance_service.main:app --reload --port 8002

   # Node.js gateway
   cd prepchef
   npm run dev
   ```
6. **Launch the frontend**
   ```bash
   cd apps/harborhomes
   npm run dev
   ```

## Testing
- **Python**
  ```bash
  pytest
  ```
- **Frontend**
  ```bash
  cd apps/harborhomes
  npm run test
  ```

## Project Layout
```
/
├── apps/
│   ├── api_gateway/
│   ├── bookings/
│   ├── city_regulatory_service/
│   ├── compliance_service/
│   ├── federal_regulatory_service/
│   ├── harborhomes/
│   └── pricing/
├── docs/
├── infra/
├── migrations/
├── prep/
├── prepchef/
├── scripts/
├── tests/
├── docker-compose.yml
├── pyproject.toml
└── package.json
```

## Contributing
1. Create a feature branch from `main`.
2. Make changes with clear, descriptive commits.
3. Ensure tests and linters pass before opening a pull request.
4. Submit a PR describing the motivation, implementation details, and testing
   performed.

## License
This project is available under the [MIT License](LICENSE).
