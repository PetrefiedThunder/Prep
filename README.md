# Prep

## Overview

**Prep** is an enterprise compliance orchestration platform designed for commercial food preparation facilities. It provides a multi-tenant system for managing regulatory compliance across federal, state, and city jurisdictions while enabling a marketplace for commercial kitchen rental operations.

### Core Mission
Enable commercial kitchens to verify and maintain compliance across all regulatory jurisdictions (FDA, state health departments, city regulations) while facilitating a marketplace for kitchen rental during off-hours.

### Architecture
Microservices-based platform with:
- **28 microservices** in `/apps` including regulatory engines, compliance services, and marketplace operations
- **Frontend Layer**: React/Next.js applications (HarborHomes, Web)
- **API Gateway**: Node.js backend (prepchef)
- **Compliance & Regulatory Engines**: Python FastAPI microservices
- **Data & Event Pipeline**: Kafka-based streaming/batch processing
- **Infrastructure**: Docker, Kubernetes (Helm), PostgreSQL, Redis, MinIO

## Technology Stack

### Backend
- **Python**: FastAPI (0.110+), SQLAlchemy (2.0+), Pydantic, asyncio/asyncpg
- **Node.js**: Express, Fastify, Stripe integration, Socket.io
- **Database**: PostgreSQL (primary), SQLite (regulatory data), Redis (cache/sessions)
- **Storage**: MinIO (S3-compatible), boto3
- **Messaging**: Kafka (aiokafka)
- **Authentication**: JWT (PyJWT), role-based access control

### Frontend
- **React/Next.js**: Vite, TypeScript, TailwindCSS
- **State Management**: Zustand, React Query, Context API
- **Internationalization**: next-intl (English, Spanish)
- **Components**: FullCalendar, shadcn-inspired components
- **Testing**: Vitest, Playwright, Testing Library, Axe (a11y)

### Infrastructure & DevOps
- **Containerization**: Docker (multi-stage builds)
- **Orchestration**: Kubernetes with Helm charts
- **CI/CD**: GitHub Actions (linting, testing, building, E2E)
- **Monitoring**: Prometheus, Grafana, Sentry
- **Deployment**: Vercel (frontend), Railway/Fly.io (backend options)
- **Code Quality**: Ruff (Python linter), mypy (type checking), ESLint, Prettier

## Key Features

### Regulatory Engine (Production Ready)
- **Federal Layer** (`/apps/federal_regulatory_service`):
  - 2 FDA Accreditation Bodies (ANAB, IAS)
  - 15 Certification Bodies (NSF, SAI Global, etc.)
  - 8 FSMA Food Safety Program Scopes
  - Authority chain validation (FDA → AB → CB → Facility)
  - Expiration monitoring with priority levels
  - ETL pipeline for automated data refresh
  - 50+ integration tests with comprehensive documentation

- **City Layer** (`/apps/city_regulatory_service`):
  - 8 major US cities (NYC, SF, Chicago, Atlanta, LA, Seattle, Portland, Boston)
  - City-specific health permits, business licenses, fire safety, insurance requirements
  - Integration with federal compliance layer
  - Hierarchical compliance validation (Federal → State → City)

### Booking & Availability System
- Atomic availability checking with `SELECT FOR UPDATE` for concurrency safety
- Booking hold worker with auto-release after 15 minutes
- Conflict resolution and reservation management
- Calendar view with real-time availability windows
- Redis-backed caching with PostgreSQL as source of truth

### Payments & Financial
- **Stripe Integration**: Connect accounts, payment intents, webhooks
- **Refund Engine**: Full/partial refunds with idempotency keys
- **Platform Fees**: Configurable fee calculation (default 15%)
- **Payout Service**: Automated weekly CSV generation for host payouts
- **Payment Reconciliation**: Automated Stripe reconciliation

### Compliance & Verification
- Food safety compliance engine with JSON summaries
- Certificate of Insurance (COI) validation
- OCR-based document metadata extraction (Tesseract)
- Health certification upload and admin review
- HBS model validation for consistency
- Comprehensive input validation with Zod/Joi

### Analytics & Insights
- Host metrics materialized view (`mv_host_metrics`)
- Kitchen utilization tracking
- Earnings and revenue analytics
- Booking funnel metrics
- Custom Grafana dashboards

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)
- PostgreSQL 14+ (if not using Docker)

### Option 1: Docker Compose (Recommended)

Start all services with a single command:

```bash
docker-compose up -d
```

This starts 6 services:
- **PostgreSQL** (port 5432): Primary database with PostGIS
- **Redis** (port 6379): Cache and session storage
- **MinIO** (port 9000): S3-compatible object storage
- **Node API** (port 3000): PrepChef marketplace backend
- **Python Compliance** (port 8000): FastAPI compliance services
- **Frontend** (port 3001): React/Next.js web application

### Option 2: Local Development

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd Prep
   ```

2. **Set up Python environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   ```

3. **Install Node.js dependencies:**
   ```bash
   cd prepchef
   npm install
   cd ..
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

   Required variables:
   ```
   DATABASE_URL=postgresql://user:pass@localhost:5432/prep
   REDIS_URL=redis://localhost:6379
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   JWT_SECRET=your-secret-key
   MINIO_ENDPOINT=localhost:9000
   MINIO_ACCESS_KEY=minioadmin
   MINIO_SECRET_KEY=minioadmin
   ```

5. **Run database migrations:**
   ```bash
   psql $DATABASE_URL < migrations/001_initial_schema.sql
   psql $DATABASE_URL < migrations/002_add_availability.sql
   # ... run all migrations in order
   python scripts/refresh_views.py  # Populate materialized views
   ```

6. **Start services:**
   ```bash
   # Terminal 1: Start compliance service
   cd apps/federal_regulatory_service
   uvicorn main:app --reload --port 8000

   # Terminal 2: Start Node.js API
   cd prepchef
   npm run dev

   # Terminal 3: Start frontend
   cd apps/harborhomes
   npm run dev
   ```

## Project Structure

```
/
├── apps/                    # 28 microservices
│   ├── federal_regulatory_service/  # FDA compliance engine (PROD)
│   ├── city_regulatory_service/     # City-level regulations (PROD)
│   ├── compliance_service/          # Food safety compliance (PROD)
│   ├── harborhomes/                 # Next.js marketplace demo (PROD)
│   ├── web/                         # React web app (DEV)
│   ├── policy_engine/               # Rego policy evaluation (SCAFF)
│   ├── graph_service/               # Regulatory obligation graph (SCAFF)
│   └── ... 21 more services
├── prepchef/                # Main Node.js marketplace backend
│   └── workspaces/          # npm workspaces for monorepo
├── modules/                 # Phase 13 core modules
│   ├── phase13_kitchen_safety/
│   ├── phase13_voice_coaching/
│   └── phase13_sensor_data_translation/
├── prep/                    # Shared Python utilities
│   ├── compliance/
│   ├── inventory/
│   └── regulatory/
├── data/                    # Regulatory databases
│   ├── federal/             # Federal regulatory data (SQLite)
│   └── cities/              # City regulatory data (SQLite)
├── migrations/              # SQL database migrations (12 files)
├── tests/                   # Comprehensive test suite (40+ directories)
├── infra/                   # Infrastructure as Code
│   ├── helm/                # Kubernetes Helm charts
│   ├── prometheus/          # Monitoring configuration
│   ├── grafana/             # Dashboard definitions
│   └── terraform/           # Infrastructure provisioning
├── docs/                    # Documentation
├── docker-compose.yml       # Local development environment
├── pyproject.toml           # Python dependencies
└── package.json             # Root monorepo config
```

### Service Status Legend
- **PROD**: Production-ready with comprehensive tests and documentation
- **DEV**: In active development
- **SCAFF**: Scaffolding/planning stage

## Microservices Directory (`/apps`)

| Service | Purpose | Status |
|---------|---------|--------|
| **federal_regulatory_service** | FDA compliance & certifier management | PROD |
| **city_regulatory_service** | City-level regulatory requirements | PROD |
| **compliance_service** | Food safety compliance validation | PROD |
| **harborhomes** | Next.js marketplace demo application | PROD |
| **policy_engine** | Policy evaluation engine (Rego) | SCAFF |
| **graph_service** | Regulatory obligation graph | SCAFF |
| **ingestion_service** | Data ingestion pipeline | SCAFF |
| **obligation_extractor** | Extract obligations from documents | SCAFF |
| **provenance_ledger** | Audit trail and provenance | SCAFF |
| **inventory_service** | Kitchen equipment tracking | SCAFF |
| **pricing** | Dynamic pricing calculations | SCAFF |
| **scheduling** | Calendar and schedule management | SCAFF |
| **monitor** | Health monitoring and alerting | SCAFF |
| **web** | React web application | DEV |
| ... and 14 more services | | |

## Testing

### Run Python tests:
```bash
pytest
```

### Run specific test categories:
```bash
pytest tests/federal/           # Federal regulatory tests
pytest tests/compliance/        # Compliance validation tests
pytest tests/integration/       # Integration tests
pytest tests/e2e/              # End-to-end tests
```

### Run frontend tests:
```bash
cd apps/harborhomes
npm run test          # Unit tests with Vitest
npm run test:e2e      # E2E tests with Playwright
npm run test:a11y     # Accessibility tests
```

### Load testing:
```bash
k6 run tests/load/booking_race_conditions.js
```

### Code quality:
```bash
# Python linting
ruff check .
mypy .

# JavaScript linting
npm run lint
npm run format
```

## Database

### PostgreSQL Schema
Primary tables:
- `users` - User accounts and authentication
- `kitchens` - Kitchen listings and details
- `bookings` - Reservation records with atomic locking
- `availability_windows` - Kitchen availability schedules
- `health_certifications` - Compliance documents
- `messages` - User-to-user messaging
- `reviews` - Rating and review system
- `mv_host_metrics` - Materialized view for analytics

### Regulatory Databases (SQLite)
- `/data/federal/prep_federal_layer.sqlite` - FDA accreditation bodies, certification bodies, scopes
- `/data/cities/prep_city_regulations.sqlite` - City-specific compliance requirements

### Running Migrations
```bash
# Apply all migrations
for file in migrations/*.sql; do
  psql $DATABASE_URL < "$file"
done

# Refresh materialized views
python scripts/refresh_views.py
```

## API Documentation

### Federal Regulatory Service (Port 8000)
```
GET  /healthz                     # Health check
GET  /federal/scopes              # List FSMA food safety scopes
GET  /federal/accreditation-bodies # List FDA accreditation bodies
GET  /federal/certification-bodies # List certification bodies
GET  /federal/certifiers          # List all certifiers with details
GET  /federal/certifiers/{id}     # Get specific certifier
GET  /federal/expiring            # Get expiring certifications
GET  /federal/authority-chain     # Validate FDA authority chain
POST /federal/match               # Match certifiers by activity
```

### PrepChef API (Port 3000)
See `openapi.yaml` for full OpenAPI 3.0 specification.

Key endpoints:
- `/api/kitchens` - Kitchen CRUD operations
- `/api/bookings` - Booking management
- `/api/availability` - Availability windows
- `/api/payments` - Stripe payment processing
- `/api/compliance` - Compliance validation

## Deployment

### Docker Compose (Development)
```bash
docker-compose up -d
```

### Kubernetes (Production)
```bash
cd infra/helm
helm install prep-platform . -f values.yaml
```

### Vercel (Frontend)
The frontend applications are configured for Vercel deployment:
```bash
cd apps/harborhomes
vercel deploy --prod
```

### Railway/Fly.io (Backend)
Backend services can be deployed to Railway or Fly.io using the provided configurations.

## Monitoring

### Prometheus Metrics
Available at `http://localhost:9090` when running with Docker Compose.

Key metrics:
- `http_requests_total` - Request count by endpoint
- `booking_conflicts_total` - Booking conflict rate
- `compliance_checks_total` - Compliance validation count
- `payment_transactions_total` - Payment processing metrics

### Grafana Dashboards
Available at `http://localhost:3002` (default credentials: admin/admin).

Pre-configured dashboards:
- Platform Overview (9 panels)
- Booking Funnel Analysis
- Compliance Status
- Host Performance Metrics

### Error Tracking
Sentry integration for error monitoring and alerting.

## Documentation

### Core Documentation
- [TECHNICAL_OUTLINE.md](TECHNICAL_OUTLINE.md) - MVP architecture (10,500 words)
- [FEDERAL_LAYER_IMPLEMENTATION.md](docs/FEDERAL_LAYER_IMPLEMENTATION.md) - Federal regulatory engine (14,700 words)
- [CITY_COMPLIANCE_IMPLEMENTATION.md](docs/CITY_COMPLIANCE_IMPLEMENTATION.md) - City compliance layer (19,000+ words)
- [DEVELOPER_ONBOARDING.md](docs/DEVELOPER_ONBOARDING.md) - Setup guide and troubleshooting
- [RUNBOOK.md](docs/RUNBOOK.md) - Incident response procedures
- [SECURITY.md](SECURITY.md) - Security best practices

### API Documentation
- [openapi.yaml](openapi.yaml) - OpenAPI 3.0 specification

### Implementation Tracking
- [FINAL_SUMMARY.md](FINAL_SUMMARY.md) - Implementation progress
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Feature tracking
- [ROADMAP.md](ROADMAP.md) - Phase-based development roadmap

### Module-Specific READMEs
- [prepchef/README.md](prepchef/README.md) - PrepChef marketplace backend
- [modules/README.md](modules/README.md) - Phase 13 core modules
- [phase12/README.md](phase12/README.md) - Phase 12 accessibility modules

## Recent Major Updates

### Q4 2025
- **City Compliance Layer** (PR #313) - Implemented city-level regulatory requirements for 8 major US cities with hierarchical compliance validation
- **Federal Regulatory Engine** (PR #311-312) - Complete federal food safety compliance backbone with 34 accreditor-certifier-scope relationships and authority chain validation
- **Data Plane Streaming** (PR #309) - Event platform foundation for real-time data processing with Kafka integration
- **Monorepo Restructure** (PR #310) - Reorganized services into modular microservices architecture

## Development Tools

### Linting
```bash
# Python
ruff check .
ruff format .

# JavaScript/TypeScript
npm run lint
npm run format
```

### Type Checking
```bash
# Python
mypy .

# TypeScript
npm run type-check
```

### Pre-commit Hooks
Install pre-commit hooks to ensure code quality:
```bash
pip install pre-commit
pre-commit install
```

## Contributing

1. Create a feature branch from `main`
2. Make your changes with clear, descriptive commits
3. Ensure all tests pass: `pytest && npm test`
4. Run linters: `ruff check . && npm run lint`
5. Submit a pull request with a detailed description

## Troubleshooting

### Common Issues

**Database connection errors:**
```bash
# Check PostgreSQL is running
docker-compose ps postgres
# Check connection string
echo $DATABASE_URL
```

**Redis connection errors:**
```bash
# Test Redis connectivity
redis-cli ping
```

**MinIO access errors:**
```bash
# Access MinIO console at http://localhost:9001
# Default credentials: minioadmin/minioadmin
```

**Port conflicts:**
```bash
# Check if ports are already in use
lsof -i :3000  # Node API
lsof -i :8000  # Python compliance
lsof -i :5432  # PostgreSQL
```

For more troubleshooting, see [DEVELOPER_ONBOARDING.md](docs/DEVELOPER_ONBOARDING.md).

## Security

- JWT-based authentication with bcrypt password hashing
- Role-based access control (RBAC) for all endpoints
- CORS configuration for cross-origin requests
- PII scrubbing in logs and error messages
- Stripe webhook signature verification
- SQL injection prevention via parameterized queries
- Rate limiting on API endpoints

See [SECURITY.md](SECURITY.md) for security policies and vulnerability reporting.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/PetrefiedThunder/Prep/issues)
- **Documentation**: [docs/](docs/)
- **API Docs**: [OpenAPI Specification](openapi.yaml)

## API SDK generation

The OpenAPI description for the Prep Compliance API lives at `contracts/openapi/prep.yaml`.

To update the generated client libraries:

1. Generate the TypeScript types:
   ```bash
   npm run openapi:ts
   ```
   The command emits `sdk/typescript/index.ts` using [`openapi-typescript`](https://github.com/drwpow/openapi-typescript).

2. Generate the Python SDK (requires [`openapi-python-client`](https://github.com/openapi-generators/openapi-python-client)):
   ```bash
   openapi-python-client generate \
     --path contracts/openapi/prep.yaml \
     --config contracts/openapi/openapi-python-client-config.yaml \
     --output sdk/python
   ```

Both commands should be run from the repository root. Remember to commit the resulting files.
