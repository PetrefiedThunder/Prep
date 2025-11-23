# Prep – Commercial Kitchen Compliance & Booking Platform

**Production-grade microservices platform for commercial kitchen rental marketplace with comprehensive regulatory compliance automation**

> 📘 **New to Prep?** Check out [WHAT_IS_THIS.md](./WHAT_IS_THIS.md) for a friendly introduction to the project!

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.121+-green.svg)](https://fastapi.tiangolo.com)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6+-blue.svg)](https://www.typescriptlang.org/)
[![Code Quality](https://img.shields.io/badge/ruff-passing-green.svg)](https://github.com/astral-sh/ruff)
[![Security](https://img.shields.io/badge/security-0%20HIGH-green.svg)](./SECURITY.md)

---

## 🎯 Overview

Prep is an enterprise-grade platform connecting certified commercial kitchens with food entrepreneurs, handling end-to-end regulatory compliance, booking orchestration, and payment processing across multiple jurisdictions.

**Core Capabilities:**
- 🏛️ **Multi-Jurisdiction Compliance**: Automated federal (FDA/FSMA) and municipal regulatory verification
- 📅 **Smart Booking Engine**: Conflict detection, availability management, and atomic transactions
- 💳 **Payment Processing**: Stripe Connect integration with split payments and automated payouts
- 🔐 **Enterprise Security**: JWT authentication, RBAC, audit logging, and comprehensive security scanning
- 📊 **Regulatory Intelligence**: Document OCR, certificate verification, and compliance tracking

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Development](#development)
- [Testing](#testing)
- [Security](#security)
- [Recent Improvements](#recent-improvements)
- [Project Status](#project-status)
- [Documentation](#documentation)
- [Contributing](#contributing)

---

## 🚀 Quick Start

### Prerequisites

- Docker 24+ with Docker Compose 2+
- Python 3.11+ (or use pyenv)
- Node.js 20+ and npm 10+
- PostgreSQL 15+ (via Docker)
- Redis 7+ (via Docker)

### One-Command Setup

```bash
git clone https://github.com/PetrefiedThunder/Prep.git && cd Prep
make bootstrap      # Installs deps, starts services, runs migrations
make health         # Verify all services are ready
```

### Manual Setup

```bash
# 1. Install Python dependencies
python -m venv .venv && source .venv/bin/activate
pip install -e . && pip install -r requirements.txt

# 2. Install Node.js dependencies
cd prepchef && npm install
cd ../apps/harborhomes && npm install

# 3. Configure environment
cp .env.example .env
# Edit .env with your configuration

# 4. Start infrastructure
docker-compose up -d postgres redis minio

# 5. Run migrations
make migrate

# 6. Start services
# Terminal 1: API Gateway
uvicorn api.index:app --reload --port 8000

# Terminal 2: Node.js services
cd prepchef && npm run dev

# Terminal 3: Frontend
cd apps/harborhomes && npm run dev
```

**Service Endpoints:**
- Frontend: http://localhost:3001
- API Gateway: http://localhost:8000/docs (OpenAPI)
- Node Backend: http://localhost:3000/docs
- MinIO Console: http://localhost:9001

---

## 🏗️ Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────┐
│                   Load Balancer / Ingress                    │
└──────────────┬──────────────────────┬───────────────────────┘
               │                      │
       ┌───────▼────────┐    ┌───────▼──────────────┐
       │  API Gateway   │    │  Next.js Frontend    │
       │  (FastAPI)     │    │  (SSR/ISR)          │
       │  Port 8000     │    │  Port 3001          │
       └───────┬────────┘    └───────┬──────────────┘
               │                      │
       ┌───────▼──────────────────────▼──────────────┐
       │        Microservices Layer                   │
       ├──────────────┬───────────────┬───────────────┤
       │ Python       │  TypeScript   │  Workers      │
       │ Services     │  Services     │  (Celery)     │
       │              │               │               │
       │ • Compliance │ • auth-svc    │ • ETL         │
       │ • Federal    │ • booking-svc │ • Notifications│
       │ • City Reg   │ • payments    │ • Analytics   │
       │ • Pricing    │ • listings    │               │
       └──────────────┴───────────────┴───────────────┘
                          │
       ┌──────────────────┴───────────────────────┐
       │      Data & Cache Layer                  │
       ├──────────────────────────────────────────┤
       │ PostgreSQL 15 │ Redis 7 │ Neo4j │ MinIO  │
       │ (ACID + GIS)  │ (Cache) │(Graph)│(Files) │
       └──────────────────────────────────────────┘
```

### Request Flow

1. **Ingress** → Load balancer routes to appropriate service
2. **Authentication** → JWT validation + database lookup
3. **Authorization** → RBAC middleware checks permissions
4. **Validation** → Pydantic/Zod schema validation
5. **Business Logic** → Service handler (async)
6. **Persistence** → Database operations (transactional)
7. **Caching** → Redis for frequently accessed data
8. **Response** → JSON serialization
9. **Audit** → Comprehensive logging with context

### Bounded Contexts (DDD)

- **Regulatory Domain**: Federal/municipal compliance verification
- **Booking Domain**: Reservations, availability, conflict detection
- **Payment Domain**: Stripe integration, settlements, ledger
- **Compliance Domain**: Document processing, OCR, admin review
- **Identity Domain**: Authentication, authorization, user management

---

## 🛠️ Tech Stack

### Backend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **API Framework** | FastAPI | 0.121+ | Async web framework |
| **ORM** | SQLAlchemy | 2.0+ | Python database ORM |
| **Validation** | Pydantic | v2+ | Runtime validation |
| **Migrations** | Alembic | Latest | Database versioning |
| **Task Queue** | Celery | Latest | Async job processing |
| **HTTP Client** | httpx | 0.25+ | Async HTTP requests |

**TypeScript Services:**
- Fastify (high-performance HTTP)
- Prisma (type-safe ORM)
- Zod (runtime validation)
- Jest + Supertest (testing)
- Winston (structured logging)

### Data Layer

| Database | Purpose | Configuration |
|----------|---------|---------------|
| **PostgreSQL 15** | Primary OLTP | ACID transactions, connection pooling |
| **PostGIS** | Geospatial queries | Kitchen location-based search |
| **Redis 7** | Sessions, cache, locks | Sentinel-enabled, RDB/AOF persistence |
| **Neo4j** | Authority graphs | FDA accreditation chain validation |
| **SQLite** | Regulatory reference data | Embedded, read-only in production |
| **MinIO** | S3-compatible storage | Documents, photos, compliance files |

### Frontend

- **Next.js 14** (App Router, SSR/ISR)
- **TypeScript** (strict mode)
- **React** (server/client components)
- **TailwindCSS** (styling)
- **Playwright** (E2E testing)

### Infrastructure

- **Docker** + **Docker Compose** (local development)
- **Kubernetes** + **Helm** (production deployment)
- **GitHub Actions** (23 CI/CD workflows)
- **Prometheus** + **Grafana** (observability)
- **Gitleaks** (secret scanning)

---

## 💻 Development

### Essential Commands

```bash
# Service management
make up              # Start all services
make down            # Stop all services
make restart         # Restart services
make logs            # Tail service logs

# Database
make migrate         # Run pending migrations
make migrate-down    # Rollback last migration
make db-reset        # ⚠️  Destroy and reinitialize

# Code quality
make lint            # Run all linters (ruff, eslint, mypy)
make format          # Auto-format code (black, prettier)
make typecheck       # Type checking (mypy, tsc)
make quality-check   # Full quality gate

# Testing
make test            # Run all tests
make test-unit       # Unit tests only
make test-integration # Integration tests
make test-e2e        # End-to-end tests
make coverage        # Generate coverage report

# Health checks
make health          # Check all services
```

### Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/your-feature

# 2. Make changes and test
make lint && make typecheck && make test

# 3. Commit with conventional commits
git add .
git commit -m "feat: add new feature"

# 4. Push and create PR
git push origin feature/your-feature
```

### Code Standards

| Language | Style | Type Check | Coverage Target |
|----------|-------|-----------|-----------------|
| **Python** | Black (100 chars) | mypy (strict) | 80%+ |
| **TypeScript** | Prettier | tsc (strict) | 80%+ |
| **Commits** | Conventional Commits | - | - |

---

## 🧪 Testing

### Test Structure

```
tests/
├── unit/               # Fast, isolated, mocked dependencies
├── integration/        # Real databases, mocked external APIs
├── e2e/               # Full request flows
├── smoke/             # Import and startup validation
├── perf/              # Performance benchmarks
├── load/              # Scalability tests
└── regression/        # Golden-file tests
```

### Running Tests

```bash
# Python tests
pytest                          # All Python tests
pytest -m integration           # Integration tests only
pytest --cov=prep              # With coverage
pytest -xvs tests/auth/        # Specific module, verbose

# TypeScript tests
cd prepchef && npm test        # All TS tests
npm run test:watch             # Watch mode
npm run test:coverage          # With coverage

# E2E tests
cd apps/harborhomes
npm run test:e2e               # Playwright E2E tests
```

### Test Coverage

**Current Status:**
- Python: ~51% (target: 80%+)
- TypeScript: TBD (target: 80%+)
- Security-critical paths: 100% required

---

## 🔒 Security

### Security Posture

**Latest Security Audit (Nov 2025):**
- ✅ **0 HIGH severity vulnerabilities**
- ✅ **2 MEDIUM issues** (false positives, documented)
- ✅ **Zero linting errors** (down from 974)
- ✅ **100% reduction** in auto-fixable issues

### Authentication & Authorization

```python
# All API endpoints enforce authentication
from prep.auth.core import get_current_active_user

@app.get("/api/protected")
async def protected_route(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session)
):
    # JWT validated + DB lookup performed
    # User is guaranteed active and not suspended
    return {"user_id": user.id}
```

**Security Features:**
- JWT tokens (15min access, 7-day refresh)
- Database-backed session validation
- RBAC with granular permissions
- Rate limiting and throttling
- Audit logging for all operations
- Secrets management (no hardcoded keys)
- TLS in transit, encryption at rest
- Regular dependency scanning (Dependabot)
- Pre-commit secret scanning (Gitleaks)

### Input Validation

All inputs validated via Pydantic (Python) or Zod (TypeScript):

```python
from pydantic import BaseModel, UUID4, Field

class BookingRequest(BaseModel):
    kitchen_id: UUID4
    start_time: datetime
    duration_hours: int = Field(gt=0, le=24)
    notes: str = Field(max_length=500)
```

### Security Scanning

```bash
# Weekly security check
./security_weekly_check.sh

# Monthly comprehensive audit
./security_monthly_audit.sh

# Manual verification
./verify_security.sh
```

---

## 📈 Recent Improvements

### November 2025 Updates

**Code Quality (PR #499)**
- ✅ **100% reduction in linting errors** (276 → 0)
- ✅ **89% reduction in medium security issues** (19 → 2)
- ✅ Fixed all unused imports and ordering issues
- ✅ Applied consistent code formatting

**Security Fixes (PR #497, #524)**
- ✅ Fixed thread-unsafe Stripe API key (BUG-003)
- ✅ Fixed race condition in idempotency middleware (BUG-002)
- ✅ Removed duplicate admin authentication functions (BUG-001)
- ✅ Added HTTP timeouts to prevent DoS
- ✅ Changed default host binding to 127.0.0.1 (localhost)

**New Features**
- ✅ Vendor verification service (PR #525)
- ✅ Comprehensive Claude Code configuration (.claude/)
- ✅ Database compatibility improvements
- ✅ Enhanced test coverage for auth paths

**Documentation**
- ✅ Implementation status assessment (25-35% MVP complete)
- ✅ MVP happy path implementation guide
- ✅ Critical bug fixes documentation
- ✅ Claude Code setup and agent profiles

---

## 📊 Project Status

<<<<<<< HEAD
### Current State (November 2025)

**Overall MVP Completion: ~25-35%**

=======
### Current State (November 19, 2025)

**Overall MVP Completion: ~25-35%**

- ✅ **Data layer is real, not stubbed**: PrepChef microservices connect to PostgreSQL (with Redis locks for availability) and the payments webhook path persists to Postgres.
- ⚠️ **Frontend is still mock-only**: HarborHomes routes and mock-data utilities serve static responses; no backend connectivity is wired yet.
- ⚠️ **Integrations remain placeholders**: San Francisco portal clients return canned data and the AI agent framework is a stub with synthetic responses.
- ❌ **End-to-end flows are incomplete**: No user journey runs from signup → booking → payment without manual intervention.

>>>>>>> origin/main
| Component | Status | Notes |
|-----------|--------|-------|
| **Database Schemas** | ✅ 90% | Prisma (17 models) + SQLAlchemy (40+ models) |
| **Authentication** | ✅ 70% | JWT + DB validation, auth-svc functional |
| **Federal Compliance** | ✅ 80% | FDA tracking, authority chains |
| **City Compliance** | ✅ 75% | 8+ cities, cost estimation |
<<<<<<< HEAD
| **Booking Engine** | ⚠️ 40% | Conflict detection exists, needs API wiring |
| **Payment Processing** | ⚠️ 50% | Python service ready (bugs fixed), TS service mock |
| **Admin Workflows** | ⚠️ 30% | OCR works, needs queue UI |
| **Frontend** | ❌ 20% | Next.js structure ready, mostly mocked |
=======
| **Booking Engine** | ⚠️ 40% | Conflict detection + Postgres/Redis wiring; still not exposed end-to-end |
| **Payment Processing** | ⚠️ 50% | Python service hardened; TS service partly mock but DB-backed webhooks |
| **Admin Workflows** | ⚠️ 30% | OCR works, needs queue UI |
| **Frontend** | ❌ 20% | Next.js structure ready, currently mock data only |
>>>>>>> origin/main
| **E2E Flows** | ❌ 15% | No complete user journeys wired |

### Active Work

**Current Focus:**
1. Database connectivity standardization (Prisma)
2. Real Stripe integration in TypeScript services
3. End-to-end MVP happy path implementation
4. Frontend integration with real APIs
5. Test coverage improvements (target: 80%+)

**Next Milestones:**
- [ ] Complete user registration flow
- [ ] Wire booking service to payments
- [ ] Implement kitchen listing creation
- [ ] Add file upload for photos/documents
- [ ] Create first E2E test for booking flow
- [ ] Deploy staging environment

---

## 📚 Documentation

### Core Documentation

- **[CLAUDE.md](./CLAUDE.md)** - Quick reference for Claude Code development sessions
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - Contribution guidelines and standards
- **[SECURITY.md](./SECURITY.md)** - Security policies and reporting
- **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Common issues and solutions
- **[DEVELOPER_ONBOARDING.md](./DEVELOPER_ONBOARDING.md)** - New developer guide

### Technical Deep Dives

- **[docs/deep-dive/AUTHENTICATION_DEEP_DIVE.md](./docs/deep-dive/AUTHENTICATION_DEEP_DIVE.md)** - Auth architecture
- **[docs/PREP_MVP_IMPLEMENTATION_PLAN.md](./docs/PREP_MVP_IMPLEMENTATION_PLAN.md)** - MVP roadmap
- **[docs/MVP_HAPPY_PATH_IMPLEMENTATION.md](./docs/MVP_HAPPY_PATH_IMPLEMENTATION.md)** - Implementation guide
- **[docs/IMPLEMENTATION_STATUS_2025-11-16.md](./docs/IMPLEMENTATION_STATUS_2025-11-16.md)** - Current status
- **[docs/architecture.md](./docs/architecture.md)** - System architecture
- **[docs/compliance_engine.md](./docs/compliance_engine.md)** - Regulatory compliance details

### Bug Tracking

- **[CRITICAL_BUGS_HUNTING_LIST.md](./CRITICAL_BUGS_HUNTING_LIST.md)** - Known critical bugs
- **[BUG_AUDIT_AND_FIX_SUMMARY_2025-11-17.md](./BUG_AUDIT_AND_FIX_SUMMARY_2025-11-17.md)** - Recent fixes
- **[REMAINING_ISSUES_REPORT.md](./REMAINING_ISSUES_REPORT.md)** - Outstanding issues

---

## 🏢 Project Structure

```
Prep/
├── .claude/                    # Claude Code configuration
│   ├── CONTEXT.md             # Repository context
│   ├── agents/                # AI agent profiles
│   ├── commands/              # Custom slash commands
│   └── workflows/             # Development workflows
├── api/                        # Python API Gateway
│   └── index.py               # Main FastAPI application
├── apps/                       # Application services
│   ├── federal_regulatory_service/
│   ├── city_regulatory_service/
│   ├── compliance_service/
│   ├── vendor_verification/   # New: Vendor verification
│   └── harborhomes/           # Next.js frontend
├── docs/                       # Documentation
├── infra/                      # Infrastructure as Code
│   ├── helm/                  # Kubernetes charts
│   └── terraform/             # Terraform configs
├── migrations/                 # Database migrations
├── prep/                       # Python shared libraries
│   ├── auth/                  # Authentication core
│   ├── compliance/            # Compliance engines
│   ├── payments/              # Stripe integration
│   ├── regulatory/            # Regulatory logic
│   ├── database/              # Database utilities
│   └── models/                # SQLAlchemy models
├── prepchef/                   # TypeScript microservices
│   ├── services/              # 13 microservices
│   │   ├── auth-svc/
│   │   ├── booking-svc/
│   │   ├── payments-svc/
│   │   ├── listing-svc/
│   │   └── ...
│   ├── packages/              # Shared packages
│   │   ├── common/
│   │   ├── database/          # Prisma client
│   │   └── types/
│   └── prisma/                # Prisma schema
├── scripts/                    # Utility scripts
├── tests/                      # Test suites
├── .github/workflows/          # CI/CD (23 workflows)
├── docker-compose.yml         # Local development
├── Dockerfile                 # Production image
├── Makefile                   # Development automation
├── pyproject.toml             # Python config
├── package.json               # Root npm workspace
└── README.md                  # This file
```

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for:

- Code of conduct
- Development workflow
- Code standards
- Testing requirements
- PR process
- Security guidelines

### Quick Contribution Checklist

- [ ] Code follows project style (Black, Prettier)
- [ ] All tests pass (`make test`)
- [ ] Linting passes (`make lint`)
- [ ] Type checking passes (`make typecheck`)
- [ ] New features have tests (80%+ coverage)
- [ ] Security best practices followed
- [ ] Documentation updated
- [ ] Commit messages follow Conventional Commits
- [ ] PR description uses template

---

## 📜 License

This project is licensed under the **MIT License** – see [LICENSE](./LICENSE) for details.

---

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) – Modern Python web framework
- [Next.js](https://nextjs.org/) – React framework for production
- [Stripe](https://stripe.com/) – Payment processing infrastructure
- [PostgreSQL](https://www.postgresql.org/) – Reliable relational database
- [Redis](https://redis.io/) – High-performance caching
- [Prisma](https://www.prisma.io/) – Next-generation ORM

Special thanks to all contributors and the open-source community.

---

## 📞 Support

- **Repository**: https://github.com/PetrefiedThunder/Prep
- **Issues**: https://github.com/PetrefiedThunder/Prep/issues
- **Security**: See [SECURITY.md](./SECURITY.md)
- **Discussions**: https://github.com/PetrefiedThunder/Prep/discussions

---

**Prep** – Simplifying compliance for the commercial kitchen sharing economy.

<<<<<<< HEAD
*Last Updated: November 2025*
=======
*Last Updated: November 19, 2025*
>>>>>>> origin/main
