# Prep

**Enterprise Compliance Orchestration for Commercial Kitchen Sharing**

Prep is a production-ready compliance and marketplace platform that automates regulatory verification, booking management, and payment processing for the commercial kitchen sharing economy. Built for scale with comprehensive security hardening, extensive testing, and enterprise-grade infrastructure.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Core Services](#core-services)
- [Technology Stack](#technology-stack)
- [Getting Started](#getting-started)
- [Development](#development)
- [Testing](#testing)
- [Security](#security)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Prep solves the complex regulatory compliance challenges in commercial kitchen sharing by automating:

- **Federal & Municipal Compliance**: Automated tracking of FDA accreditation chains and city-specific permit requirements across major U.S. cities
- **Document Verification**: OCR-powered processing of licenses, certifications, and food safety records
- **Booking Management**: Atomic reservations with concurrency safety and availability holds
- **Payment Processing**: Full Stripe integration with charges, refunds, platform fees, and Connect payouts
- **Regulatory Intelligence**: Real-time monitoring of certification expiration and authority chain validation

### Key Differentiators

- **Hybrid Architecture**: Python microservices for regulatory logic + Node.js services for business flows
- **Multi-Layer Compliance**: Federal (FDA/FSMA) + Municipal (8 major cities) + Facility-level verification
- **Production Hardened**: Docker security, secret scanning, comprehensive test harness, pre-commit hooks
- **Developer Experience**: One-command bootstrap, extensive documentation, automated migrations

---

## Architecture

Prep uses a **microservices architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Gateway                              │
│                    (FastAPI Orchestration)                       │
└────────────┬────────────────────────────────────────────────────┘
             │
      ┌──────┴──────┐
      │             │
┌─────▼─────┐  ┌───▼────────────────────────────────────┐
│  Python   │  │         Node.js Backend                 │
│ Services  │  │          (PrepChef)                     │
│           │  │                                         │
│ • Federal │  │  • Authentication    • Notifications    │
│   Reg Svc │  │  • Bookings         • Pricing          │
│ • City    │  │  • Listings         • Access Control   │
│   Reg Svc │  │  • Payments         • Admin            │
│ • Compli  │  │  • Availability     • Audit            │
│   ance    │  │                                         │
└─────┬─────┘  └───┬────────────────────────────────────┘
      │            │
      └─────┬──────┘
            │
┌───────────▼──────────────────────────────────────────────────┐
│                    Data & Infrastructure                      │
│                                                               │
│  • PostgreSQL 15 (PostGIS)    • Redis 7 (Caching)           │
│  • MinIO (S3-compatible)      • Neo4j (Graph DB)            │
│  • SQLite (Regulatory Data)   • Prometheus (Monitoring)     │
└───────────────────────────────────────────────────────────────┘
```

### Design Principles

- **Domain-Driven Design**: Clear bounded contexts for regulatory, booking, and payment domains
- **Event Sourcing**: Audit logs for all compliance decisions and state transitions
- **Immutable Infrastructure**: Containerized services with declarative configuration
- **Defense in Depth**: Multiple security layers from network to application to data

For detailed architecture documentation including SPOF analysis and RTO/RPO targets, see [`docs/architecture.md`](docs/architecture.md).

---

## Core Services

### Python Services (`apps/`)

#### **Federal Regulatory Service**
- FDA accreditation and certification tracking under FSMA
- Authority chain validation (FDA → Accreditation Body → Certification Body → Facility)
- Automated expiration monitoring and renewal reminders
- ETL pipeline for ANAB/IAS accreditation directories
- SQLite-backed federal reference data

#### **City Regulatory Service**
- Municipal permit requirements for 8+ major U.S. cities
- City-specific health code validation
- Regulatory fee estimation and cost projections
- ETL adapters for diverse municipal data sources
- Normalized compliance API across jurisdictions

#### **Compliance Service**
- Document upload and validation workflows
- OCR processing for licenses and certifications
- Certificate verification and authenticity checks
- Admin review interfaces and approval workflows
- Integration with federal and city regulatory engines

#### **Bookings Service**
- Atomic reservation creation with ACID guarantees
- Conflict detection and optimistic locking
- Hold workers for temporary availability locks
- Calendar synchronization and availability management

#### **API Gateway**
- Request routing and load balancing
- Authentication and authorization enforcement
- Rate limiting and quota management
- OpenAPI documentation generation

#### **Pricing Service**
- Dynamic fee calculation engine
- Platform fee and payment splitting logic
- Promotional pricing and discount codes

### Node.js Backend (`prepchef/`)

Modern TypeScript microservices architecture with **13 specialized services**:

- **auth-svc**: JWT authentication, email verification, session management
- **booking-svc**: Booking creation, conflict detection, status management
- **listing-svc**: Kitchen CRUD, search, geospatial queries (PostGIS)
- **payments-svc**: Stripe integration, payment intents, Connect payouts
- **compliance-svc**: Document upload, admin review, status tracking
- **availability-svc**: Calendar management with Redis caching
- **notif-svc**: Email (Resend), SMS (Twilio), push notifications
- **admin-svc**: Certification approval, user moderation, analytics
- **audit-svc**: Comprehensive audit logging
- **pricing-svc**: Fee calculation and dynamic pricing
- **access-svc**: Fine-grained access control
- **common**: Shared utilities and business logic

### Frontend (`apps/harborhomes/`)

**Next.js 14** marketplace application:
- TypeScript + React with App Router
- Server-side rendering for SEO
- Playwright E2E test coverage
- Host onboarding and renter booking flows
- Real-time availability calendar
- Document upload and verification UI

### Shared Libraries

#### **prep/** (Python)
40+ shared modules including:
- **compliance/**: Regulatory rule engines
- **payments/**: Stripe SDK wrappers
- **regulatory/**: Data ingestion and analytics
- **database/**: SQLAlchemy models
- **auth/**: Authentication utilities
- **notifications/**: Email/SMS delivery
- **analytics/**: Metrics and dashboards
- **integrations/**: Third-party API clients

#### **prepchef/packages/** (Node.js)
- **@prep/common**: Shared TypeScript utilities
- **@prep/logger**: Structured logging (Winston)
- **@prep/database**: Prisma ORM wrappers
- **@prep/config**: Environment configuration
- **@prep/types**: Generated OpenAPI types

---

## Technology Stack

### Backend

**Python** (Microservices)
- FastAPI 0.121+ (async web framework)
- SQLAlchemy 2.0 (ORM)
- Alembic (migrations)
- Pydantic (data validation)
- Celery (task queue)
- pytest + hypothesis (testing)

**Node.js 20+** (Business Services)
- TypeScript 5.6+
- Fastify (high-performance HTTP)
- Prisma (type-safe ORM)
- Zod (runtime validation)
- Jest + Supertest (testing)

### Databases

- **PostgreSQL 15** with PostGIS (geospatial)
- **Redis 7** with persistence (caching, sessions)
- **Neo4j** (regulatory relationship graphs)
- **SQLite** (immutable regulatory reference data)
- **MinIO** (S3-compatible object storage)

### Infrastructure

- **Docker** & **Docker Compose** (local development)
- **Helm Charts** (Kubernetes deployment)
- **GitHub Actions** (CI/CD with 23 workflows)
- **Prometheus** + **Grafana** (monitoring)
- **OpenTelemetry** (distributed tracing)
- **Gitleaks** (secret scanning)

### External Integrations

- **Stripe** (payments, Connect payouts)
- **AWS** (S3, SES, Secrets Manager)
- **Resend** (transactional email)
- **Twilio** (SMS notifications)

---

## Getting Started

### Prerequisites

- **Docker** 24+ and **Docker Compose** 2+
- **Python** 3.10+ with pip
- **Node.js** 20+ with npm
- **PostgreSQL** 15+ (or use Docker)
- **Redis** 7+ (or use Docker)

### Quick Start (Recommended)

Bootstrap the entire development environment with one command:

```bash
# Clone the repository
git clone <repo-url>
cd Prep

# Bootstrap environment (installs deps, starts services, runs migrations)
make bootstrap

# Verify all services are healthy
make health
```

This will:
1. Install Python and Node.js dependencies
2. Start PostgreSQL, Redis, and MinIO via Docker Compose
3. Run database migrations
4. Start all microservices
5. Verify connectivity and health checks

### Manual Setup

If you prefer step-by-step setup:

#### 1. Install Dependencies

```bash
# Python dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .

# Node.js dependencies (prepchef backend)
cd prepchef
npm install

# Frontend dependencies
cd apps/harborhomes
npm install
```

#### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env.local

# Edit with your local settings
nano .env.local

# Export environment variables
export $(cat .env.local | xargs)
```

Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `STRIPE_SECRET_KEY`: Stripe API key
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`: AWS credentials
- `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`: MinIO credentials

#### 3. Start Infrastructure Services

```bash
# Start PostgreSQL, Redis, MinIO
docker-compose up -d postgres redis minio

# Verify connectivity
make check-db
```

#### 4. Run Database Migrations

```bash
# Run all migrations (SQL + Alembic)
make migrate

# Or manually:
psql $DATABASE_URL < migrations/init.sql
for file in migrations/00*.sql; do
  [ "$(basename "$file")" = "init.sql" ] && continue
  psql $DATABASE_URL < "$file"
done
```

#### 5. Start Services

```bash
# Terminal 1: Federal Regulatory Service
uvicorn apps.federal_regulatory_service.main:app --reload --port 8000

# Terminal 2: City Regulatory Service
uvicorn apps.city_regulatory_service.main:app --reload --port 8001

# Terminal 3: Compliance Service
uvicorn apps.compliance_service.main:app --reload --port 8002

# Terminal 4: Node.js Backend
cd prepchef
npm run dev

# Terminal 5: Frontend
cd apps/harborhomes
npm run dev
```

#### 6. Access Services

- Frontend: http://localhost:3001
- API Gateway: http://localhost:8000/docs
- Node.js Backend: http://localhost:3000/docs
- MinIO Console: http://localhost:9001

---

## Development

### Development Commands

```bash
# Start all services
make up

# Stop all services
make down

# View logs
make logs

# Restart services
make restart

# Clean environment (removes volumes!)
make clean
```

### Database Operations

```bash
# Run migrations
make migrate

# Rollback last migration
make migrate-down

# Create new migration
alembic revision -m "description"

# Reset database (WARNING: destroys data)
make db-reset
```

### Code Quality

```bash
# Run all linters
make lint

# Run type checking
make typecheck

# Format code
make format

# Run pre-commit hooks manually
pre-commit run --all-files
```

### Development Workflow

1. **Create a feature branch** from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes** with frequent commits
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

3. **Run tests** before pushing
   ```bash
   make test
   make lint
   make typecheck
   ```

4. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### Troubleshooting

If you encounter issues, see [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) for solutions to:
- Missing environment variables
- Database connection failures
- Module import errors
- Docker Compose networking issues
- Port conflicts
- Memory/resource constraints

---

## Testing

Prep has **comprehensive test coverage** across multiple layers:

### Test Commands

```bash
# Run all tests (Python + Node.js)
make test

# Python tests only
pytest

# Python tests with coverage
pytest --cov=prep --cov-report=html

# Node.js tests only
cd prepchef && npm test

# E2E tests
npm run test:e2e

# Smoke tests (validates imports)
make smoke-test

# Load/performance tests
make test:load
```

### Test Organization

```
tests/
├── unit/           # Fast, isolated unit tests
├── integration/    # Service integration tests
├── e2e/           # End-to-end user flows
├── smoke/         # Import and basic functionality
├── perf/          # Performance benchmarks
├── load/          # Load testing scenarios
├── contract/      # API contract tests
└── regression/    # Regression test suite
```

### Test Markers

Use pytest markers to run specific test categories:

```bash
# Integration tests only
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# E2E tests only
pytest -m e2e

# Compliance-specific tests
pytest tests/compliance/
```

### Continuous Integration

GitHub Actions runs on every push:
- ✅ Unit and integration tests
- ✅ Linting (Ruff, ESLint)
- ✅ Type checking (MyPy, TypeScript)
- ✅ Security scanning (Bandit, Gitleaks)
- ✅ Contract tests (OpenAPI validation)
- ✅ E2E tests (Playwright)
- ✅ Smoke tests (import validation)

See `.github/workflows/` for all 23 CI workflows.

---

## Security

Prep implements **defense-in-depth security** with multiple layers:

### Recent Security Hardening

✅ **Docker Security** (Multi-stage builds, non-root user, minimal attack surface)
✅ **Secret Scanning** (Gitleaks pre-commit hooks + GitHub Actions)
✅ **RIC Test Harness** (Regression testing for compliance engine)
✅ **Pre-commit Hooks** (Ruff, Black, Bandit, MyPy, Hadolint, yamllint)
✅ **Security Audit Scripts** (Weekly checks, monthly audits)
✅ **Architecture Documentation** (SPOF analysis, incident response)

### Security Features

- **Authentication**: JWT tokens with refresh rotation, email verification
- **Authorization**: Role-based access control (RBAC) with fine-grained permissions
- **Data Encryption**: TLS in transit, encryption at rest for PII
- **Secret Management**: AWS Secrets Manager integration, no secrets in code
- **Audit Logging**: Comprehensive audit trails for all sensitive operations
- **Input Validation**: Pydantic/Zod schemas, SQL injection prevention
- **Rate Limiting**: Per-endpoint rate limits, DDoS protection
- **Dependency Scanning**: Dependabot alerts, automated updates

### Security Scripts

```bash
# Run comprehensive security verification
./verify_security.sh

# Weekly security check
./security_weekly_check.sh

# Monthly security audit
./security_monthly_audit.sh

# Check for secrets before commit
./scripts/check_secrets.sh
```

### Reporting Security Issues

See [`SECURITY.md`](SECURITY.md) for:
- Vulnerability reporting process
- Credential rotation procedures
- Security policies
- Incident response plans

---

## Documentation

Comprehensive documentation is available in multiple locations:

### Root Documentation

- **[DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md)** – Complete developer setup guide
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** – Common issues and solutions
- **[README.local.md](README.local.md)** – Local development deep-dive
- **[RUNBOOK.md](RUNBOOK.md)** – Operational procedures and incident response
- **[SECURITY.md](SECURITY.md)** – Security policies and credential management
- **[PRIVACY.md](PRIVACY.md)** – Data handling and privacy guidelines
- **[CONTRIBUTING.md](CONTRIBUTING.md)** – Contribution guidelines and PR process
- **[CHANGELOG.md](CHANGELOG.md)** – Version history and release notes
- **[ROADMAP.md](ROADMAP.md)** – Product roadmap and future plans

### Quality & Security Reports

- **[BUG_HUNT_REPORT_2025-11-11.md](BUG_HUNT_REPORT_2025-11-11.md)** – Comprehensive bug audit (78 issues)
- **[CODE_QUALITY_ANALYSIS.md](CODE_QUALITY_ANALYSIS.md)** – Code quality assessment
- **[CODE_QUALITY_FIXES.md](CODE_QUALITY_FIXES.md)** – Actionable refactoring guide
- **[SECURITY_VULNERABILITY_REPORT.md](SECURITY_VULNERABILITY_REPORT.md)** – Security audit results
- **[CONFIG_AUDIT_REPORT.md](CONFIG_AUDIT_REPORT.md)** – Configuration audit findings

### Technical Documentation (`docs/`)

- **[architecture.md](docs/architecture.md)** – System architecture with Mermaid diagrams
- **[compliance_engine.md](docs/compliance_engine.md)** – Compliance rule engine design
- **[etl_crawler.md](docs/etl_crawler.md)** – Regulatory data ETL pipeline
- **[testing_validation_plan.md](docs/testing_validation_plan.md)** – QA strategy
- **observability/** – Monitoring and alerting setup
- **city_summaries/** – City-specific regulatory summaries

### Service Documentation

Each service has its own README:
- `apps/federal_regulatory_service/README.md`
- `apps/city_regulatory_service/README.md`
- `apps/compliance_service/README.md`
- `apps/harborhomes/README.md`
- `prepchef/README.md`

### API Documentation

- **OpenAPI Docs**: Available at `/docs` endpoint for each service
- **Postman Collection**: Import from `docs/postman/Prep.postman_collection.json`
- **API Reference**: Generated TypeScript types in `prepchef/packages/types/`

---

## Contributing

We welcome contributions! Please follow these guidelines:

### 1. Setup Development Environment

```bash
# Fork and clone the repository
git clone https://github.com/your-username/Prep.git
cd Prep

# Bootstrap environment
make bootstrap

# Install pre-commit hooks
pre-commit install
```

### 2. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` – New features
- `fix/` – Bug fixes
- `docs/` – Documentation updates
- `refactor/` – Code refactoring
- `test/` – Test additions/improvements

### 3. Make Changes

- Write clear, descriptive commit messages following [Conventional Commits](https://www.conventionalcommits.org/)
- Add tests for new functionality
- Update documentation as needed
- Ensure code passes linting and type checking

```bash
# Verify your changes
make test
make lint
make typecheck
```

### 4. Submit a Pull Request

- Provide a clear PR description using the template in `PR_DESCRIPTION.md`
- Link related issues
- Describe implementation approach
- Include screenshots for UI changes
- List testing performed

### Code Review Process

1. Automated CI checks must pass
2. At least one maintainer approval required
3. Address review feedback
4. Squash commits before merge (if requested)

### Development Guidelines

- **Python**: Follow PEP 8, use type hints, document with docstrings
- **TypeScript**: Strict mode enabled, use interfaces over types
- **Testing**: Aim for >80% coverage, write meaningful tests
- **Security**: Never commit secrets, validate all inputs
- **Documentation**: Update docs for API changes

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for detailed guidelines.

---

## Project Structure

```
Prep/
├── apps/                      # Microservices
│   ├── api_gateway/          # FastAPI gateway
│   ├── bookings/             # Booking service
│   ├── city_regulatory_service/
│   ├── compliance_service/
│   ├── federal_regulatory_service/
│   ├── harborhomes/          # Next.js frontend
│   └── pricing/              # Pricing service
├── docs/                      # Documentation
│   ├── architecture.md       # System architecture
│   ├── city_summaries/       # City regulatory docs
│   ├── deep-dive/            # Technical deep-dives
│   └── observability/        # Monitoring docs
├── infra/                     # Infrastructure as Code
│   ├── helm/                 # Kubernetes Helm charts
│   ├── terraform/            # Terraform configs
│   └── docker/               # Docker configurations
├── migrations/               # Database migrations
│   ├── init.sql              # Initial schema
│   └── 00*.sql               # Versioned migrations
├── prep/                      # Python shared libraries
│   ├── compliance/           # Compliance engines
│   ├── payments/             # Stripe integration
│   ├── regulatory/           # Regulatory logic
│   ├── database/             # SQLAlchemy models
│   ├── auth/                 # Authentication
│   └── api/                  # FastAPI routes
├── prepchef/                  # Node.js backend monorepo
│   ├── services/             # 13 microservices
│   │   ├── auth-svc/
│   │   ├── booking-svc/
│   │   ├── payments-svc/
│   │   └── ...
│   ├── packages/             # Shared packages
│   │   ├── common/
│   │   ├── database/
│   │   └── types/
│   ├── prisma/               # Prisma schema
│   └── tests/e2e/            # E2E tests
├── regengine/                 # Compliance test harness
│   └── tests/                # Golden file tests
├── scripts/                   # Utility scripts
│   ├── check_db.py           # Database verification
│   ├── check_secrets.sh      # Secret scanning
│   └── ...
├── tests/                     # Test suites
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── smoke/
│   └── perf/
├── .github/workflows/         # CI/CD (23 workflows)
├── .pre-commit-config.yaml   # Pre-commit hooks
├── docker-compose.yml        # Local development stack
├── Dockerfile                # Multi-stage production build
├── Makefile                  # Development automation
├── pyproject.toml            # Python project config
├── package.json              # Root npm workspace
├── pytest.ini                # Pytest configuration
└── README.md                 # This file
```

---

## Deployment

### Local Development

```bash
make up          # Start all services via Docker Compose
make health      # Verify all services are healthy
```

### Production Deployment

The API gateway is deployed as a containerized application:

```bash
# Build production image
docker build -t prep:latest .

# Run with Gunicorn (WSGI)
gunicorn run_api:app --workers 4 --bind 0.0.0.0:8000

# Or with Uvicorn (ASGI)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Both `main:app` and `run_api:app` call `api.index.create_app()` internally.

### Kubernetes Deployment

```bash
# Deploy with Helm
helm install prep ./infra/helm/prep -f values.production.yaml

# Verify deployment
kubectl get pods -n prep
kubectl logs -f deployment/prep-api-gateway
```

### Environment Variables

Required in production:
- `DATABASE_URL` – PostgreSQL connection string
- `REDIS_URL` – Redis connection string
- `STRIPE_SECRET_KEY` – Stripe API key
- `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- `JWT_SECRET_KEY` – JWT signing key
- `ENVIRONMENT` – `production` or `staging`

See [`RUNBOOK.md`](RUNBOOK.md) for operational procedures.

---

## Roadmap

### Recent Achievements (November 2025)

- ✅ **Comprehensive bug fixes** – 78 bugs resolved (9 critical, 9 high severity)
- ✅ **Security hardening** – Docker security, Gitleaks, pre-commit hooks
- ✅ **RIC test harness** – Regression testing for compliance engine
- ✅ **Critical bug fixes** – Dependency conflicts, service corruption, duplicate code
- ✅ **Type annotation modernization** – Modern Python type hints across codebase
- ✅ **Code quality improvements** – SQL injection fixes, secure token generation
- ✅ **Comprehensive testing infrastructure** – Smoke tests, CI workflows
- ✅ **Security vulnerability remediation** – Hardcoded secrets removal, Docker root fixes
- 🚧 Multi-city expansion (LA, Chicago, Austin)
- 🚧 Mobile app (React Native)
- 🚧 Real-time notifications (WebSockets)

### Upcoming Features

- **Q4 2025**: Automated insurance verification, production deployment hardening
- **Q1 2026**: AI-powered compliance recommendations
- **Q2 2026**: International expansion (Canada, UK)
- **Q3-Q4 2026**: Supply chain and delivery management

See [`ROADMAP.md`](ROADMAP.md) for detailed plans.

---

## Support

### Getting Help

- **Documentation**: Check docs/ for guides and troubleshooting
- **GitHub Issues**: Open an issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Email**: [Insert support email]

### Common Issues

See [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) for solutions to:
- Environment setup problems
- Database connection issues
- Import errors
- Docker networking problems

---

## License

This project is licensed under the **MIT License** – see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

Built with:
- **FastAPI** – Modern Python web framework
- **Next.js** – React framework for production
- **Stripe** – Payment processing infrastructure
- **PostgreSQL** – Reliable relational database
- **Redis** – High-performance caching

Special thanks to all contributors and the open-source community.

---

**Prep** – Simplifying compliance for the commercial kitchen sharing economy.
