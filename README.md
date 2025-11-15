# Prep – Enterprise Compliance Orchestration Platform

**Technical Platform for Regulatory Compliance, Booking Orchestration & Payment Processing**

Production microservices platform with hybrid Python/Node.js architecture, comprehensive compliance rule engines, and enterprise-grade infrastructure. Federal and municipal regulatory automation with multi-layer verification, atomic booking transactions, Stripe payment integration, and full audit trail logging.

---

## Quick Summary

| Aspect | Details |
|--------|---------|
| **Core Architecture** | Microservices: Python (FastAPI + async) + Node.js (TypeScript/Fastify) |
| **Data Layer** | PostgreSQL 15 + PostGIS, Redis 7, Neo4j, MinIO, SQLite |
| **Deployment** | Docker Compose (dev), Kubernetes/Helm (prod) |
| **APIs** | OpenAPI 3.0 with Pydantic/Zod validation, async request handling |
| **Services** | 13 Node.js μ-services + 6+ Python backends + Next.js frontend |
| **Test Coverage** | Unit, integration, E2E, smoke, load testing, golden-file regression |
| **CI/CD** | 23 GitHub Actions workflows, pre-commit hooks, security scanning |
| **Security Model** | JWT auth + RBAC, TLS, encryption-at-rest, audit logging, secret scanning |

---

## Table of Contents

- [Technical Stack](#technical-stack)
- [System Architecture](#system-architecture)
- [Core Services](#core-services)
- [Critical Implementation Details](#critical-implementation-details)
- [Known Issues & Active Bugs](#known-issues--active-bugs)
- [Testing & Validation](#testing--validation)
- [Security Architecture](#security-architecture)
- [Development Setup](#development-setup)
- [Operations & Monitoring](#operations--monitoring)
- [Known Technical Debt](#known-technical-debt)
- [Contributing](#contributing)
- [License](#license)

---

## Technical Stack

### Backend Languages & Frameworks

**Python 3.10+**
- FastAPI 0.121+ (async ASGI web framework)
- SQLAlchemy 2.0 (ORM with type-safe queries)
- Pydantic v2 (runtime validation with discriminated unions)
- Alembic (versioned migrations with branching)
- Celery (async task queue with Redis broker)
- httpx (async HTTP client with connection pooling)
- pytest + hypothesis (property-based testing)

**Node.js 20+ / TypeScript 5.6+**
- Fastify (high-performance HTTP framework)
- Prisma (type-safe ORM with query builder)
- Zod (runtime schema validation)
- Jest + Supertest (test framework)
- Winston (structured logging)
- OpenTelemetry (distributed tracing)

### Data Layer

| Database | Purpose | Configuration |
|----------|---------|----------------|
| **PostgreSQL 15** | Primary OLTP, ACID transactions | `postgresql://...` with connection pooling |
| **PostGIS** | Geospatial queries (location-based kitchen search) | Extension loaded, geometry/geography types |
| **Redis 7** | Session storage, cache, pub/sub, distributed locks | Sentinel-enabled with persistence (RDB/AOF) |
| **Neo4j** | Regulatory authority relationship graphs | Bolt protocol, Cypher queries |
| **SQLite** | Immutable reference data (FDA, municipal codes) | Read-only in production, embedded |
| **MinIO** | S3-compatible object storage | IAM credentials, bucket policies |

### Async & Concurrency

- **FastAPI**: ASGI with async/await, Starlette middleware pipeline
- **Uvicorn**: ASGI server with worker pool (typically 4 workers × CPU cores)
- **Gunicorn**: WSGI fallback (production deployment option)
- **asyncio**: Event loop for concurrent I/O operations
- **aioredis**: Async Redis client with connection pooling
- **httpx**: Non-blocking HTTP client for third-party APIs

### Deployment & Infrastructure

- **Docker**: Multi-stage builds, non-root users, minimal attack surface
- **Docker Compose**: Local development (postgres, redis, minio)
- **Kubernetes**: Helm charts for production deployment
- **GitHub Actions**: 23 CI/CD workflows (unit, integration, security, deployment)
- **Prometheus**: Metrics collection and time-series storage
- **Grafana**: Metric visualization and alerting
- **Gitleaks**: Secret scanning on every commit (pre-commit + GHA)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Load Balancer / Ingress                       │
└───────────────┬────────────────────────────┬───────────────────────┘
                │                            │
        ┌───────▼─────────┐        ┌────────▼──────────────┐
        │  API Gateway    │        │  Next.js Frontend     │
        │  (FastAPI)      │        │  (SSR/ISR)            │
        │  :8000          │        │  :3001                │
        └───────┬─────────┘        └────────┬──────────────┘
                │                            │
        ┌───────▼────────────────────────────▼──────────┐
        │     Service Mesh / Internal Networking        │
        │  (Service discovery via Docker DNS)           │
        └───────┬────────────────────────┬──────────────┘
                │                        │
    ┌───────────┴──────────┬─────────────▼────────────┐
    │                      │                          │
┌───▼──────────┐  ┌───────▼────────┐  ┌─────────────▼──────┐
│ Python       │  │  Node.js       │  │   Batch/Workers    │
│ Microsvcs    │  │  (PrepChef)    │  │   (Celery)         │
│              │  │  13 services   │  │                    │
│ • Federal    │  │  • auth        │  │ • ETL              │
│ • City       │  │  • booking     │  │ • Reconciliation   │
│ • Compliance │  │  • payments    │  │ • Notifications    │
│ • Bookings   │  │  • listings    │  │ • Analytics        │
│ • Pricing    │  │  • admin       │  └────────────────────┘
└─────────────┘  └────────────────┘
        │                │
        │                │
    ┌───┴────────────────┴──────────────────────┐
    │       Persistence & Cache Layer            │
    ├──────────────────────────────────────────┤
    │ PostgreSQL 15 │ Redis 7 │ Neo4j │ MinIO  │
    │ (ACID OPS)    │ (Cache) │(Graph)│(Files) │
    └────────────────────────────────────────────┘
        │
        └─────────► Observability
                   (Prometheus/Grafana/OpenTelemetry)
```

### Request Flow

1. **Ingress** → Load balancer routes to appropriate service
2. **Authentication** → FastAPI middleware validates JWT token
3. **Authorization** → RBAC middleware checks permissions
4. **Validation** → Pydantic schemas validate request body
5. **Business Logic** → Service handler (async function)
6. **Database** → SQLAlchemy queries with connection pooling
7. **Cache** → Redis check-then-set for frequently accessed data
8. **Response** → Pydantic model serialization → JSON
9. **Audit Trail** → Middleware logs operation with context

### Bounded Contexts (DDD)

- **Regulatory Domain**: Federal/city compliance verification
- **Booking Domain**: Reservation creation, conflict detection, holds
- **Payment Domain**: Stripe integration, reconciliation, settlements
- **Compliance Domain**: Document processing, OCR, admin review
- **Access Domain**: User authentication, authorization, role management

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

## Critical Implementation Details

### Database & Query Patterns

**PostgreSQL Connection Management**
- Uses SQLAlchemy connection pooling (default 5 connections)
- Async connections via `asyncpg` for FastAPI
- All queries use parameterized statements (Pydantic validators ensure no SQL injection)
- Transaction isolation level: `REPEATABLE_READ` for booking operations

**N+1 Query Prevention**
- Use `selectinload()` or `joinedload()` for relationship loading
- Common pitfall: Iterating `result.all()` then accessing related objects in loop
- See `jobs/reconciliation_engine.py` for pattern examples

**PostGIS Spatial Queries**
- Kitchen locations stored as `geometry(Point, 4326)` (WGS84)
- Distance calculations use `ST_Distance()` and `ST_DWithin()`
- Index on location field: `CREATE INDEX idx_kitchen_location ON kitchens USING GIST(location)`

**Redis Locking Pattern**
- Distributed locks via `SET key value NX EX timeout`
- Used for: Booking holds, idempotency checks, session validation
- Lock ownership: Each lock includes request UUID to prevent cross-request release

### Async Patterns & Pitfalls

**Safe Patterns**
```python
# ✅ Correct: Awaiting in async function
async def handler(request):
    result = await db.query(...).execute()
    return result

# ✅ Correct: Dependency injection ensures scope
async def get_user(session: Session = Depends(get_session)):
    return await session.get_user()
```

**Unsafe Patterns**
```python
# ❌ Wrong: Setting global state in async context
stripe.api_key = secret_key  # Race condition!

# ❌ Wrong: Non-atomic check-then-set
if redis.exists(key):  # Line 1
    # Another request could modify redis here
    redis.set(key, value)  # Line 2

# ❌ Wrong: Creating cache without sync
if _CACHE_CLIENT is None:  # Line 1
    # Multiple async tasks could reach here
    _CACHE_CLIENT = initialize()  # Line 2
```

### Request Context Tracking

- **Request ID**: Added by `prep/middleware/request_context.py` (X-Request-ID header)
- **User Context**: JWT claims extracted to FastAPI security dependencies
- **Audit Trail**: Middleware logs all request/response pairs
- **Error Context**: Failed requests capture stack trace with sanitized sensitive data

### Payment Integration (Stripe)

**Webhook Validation**
- Signature validation using `stripe.Webhook.construct_event()`
- Idempotency key in request headers prevents duplicate charges
- All webhook handlers are async, non-blocking

**Charge Flow**
1. Booking confirmed → Create payment intent
2. Client-side payment submission
3. Stripe webhook fires → Update booking status
4. Async task reconciles payment record with booking

### Compliance Rule Engine

**Authority Chain Validation**
- FDA → Accreditation Body (AB) → Certification Body (CB) → Facility
- Each link verified against NEO4j relationship graph
- Expiration dates checked against SQLite reference data

**City-Specific Rules**
- Configuration per city in `apps/city_regulatory_service/`
- Rules include: License types, renewal intervals, fee structures
- Rules loaded at startup, cached in Redis with TTL

### Testing Infrastructure

**Test Layers**
- **Unit**: Fast, isolated, mocked dependencies
- **Integration**: Real databases, Redis, external APIs mocked
- **E2E**: Full request flow through all services
- **Smoke**: Import validation across all modules
- **Regression**: Golden-file testing via RIC test harness

**Database Testing**
- Each test gets isolated transaction (rolled back)
- Fixtures pre-populate reference data
- Alembic migrations tested before applying to production

---

## Known Issues & Active Bugs

### 🔴 CRITICAL Bugs (Active Bug Hunt Required)

| ID | Issue | Location | Impact | Workaround |
|----|-------|----------|--------|-----------|
| **BUG-001** | Duplicate `get_current_admin()` function definition | `prep/admin/certification_api.py:289,321` | Second definition overrides first, endpoint may use wrong field names | Remove duplicate, merge implementations |
| **BUG-002** | Race condition in idempotency middleware (non-atomic check-set) | `prep/api/middleware/idempotency.py:55-71` | Concurrent requests with same idempotency key could bypass protection | Use Redis Lua script for atomic operation |
| **BUG-003** | Thread-unsafe global Stripe API key | `prep/payments/service.py:70` | Concurrent payment requests may use incorrect API key | Pass API key per-request instead of setting globally |

### 🔴 HIGH Severity Issues

| ID | Issue | Location | Impact | Fix |
|----|-------|----------|--------|-----|
| **BUG-004** | CORS origin whitespace not stripped | `api/index.py:193-195` | Valid CORS origins with whitespace fail validation | Strip each origin after split |
| **BUG-005** | Unsafe falsy checks on Stripe fields | `prep/payments/service.py:77,114` | Valid Stripe responses with falsy IDs cause errors | Use `is None` instead of truthiness |
| **BUG-006** | Incomplete DAG implementation | `dags/foodcode_ingest.py:18,32,46` | ETL pipeline non-functional (raises NotImplementedError) | Implement functions or remove DAG |
| **BUG-007** | Silent exception handling in audit logger | `middleware/audit_logger.py:61-63` | Audit trail failures go undetected | Log exception and emit metrics before returning |
| **BUG-008** | Stripe webhook idempotency not enforced | `prep/payments/service.py` | Duplicate webhook deliveries could create duplicate charges | Validate idempotency key before processing |

### 🟡 MEDIUM Severity Issues

| ID | Issue | Location | Category | Priority |
|----|-------|----------|----------|----------|
| **BUG-009** | Potential N+1 queries in reconciliation | `jobs/reconciliation_engine.py:102,125,149` | Performance | High |
| **BUG-010** | Race condition in global cache initialization | `prep/cache.py:79-102` | Concurrency | High |
| **BUG-011** | Configuration whitespace normalization inconsistent | `prep/settings.py:271,301,325` | Security | Medium |
| **BUG-012** | Token validation error lacks diagnostic logging | `prep/auth/rbac.py:116-120` | Debugging | Medium |
| **BUG-013** | Audit logger silently skips when session unavailable | `middleware/audit_logger.py:35-36` | Logging | Medium |
| **BUG-014** | Session cache validation not atomic | `prep/auth/dependencies.py:57-71` | Concurrency | Medium |
| **BUG-015** | Duplicate AdminUser model definitions | `prep/admin/certification_api.py:289-296,321-329` | Type Safety | Medium |
| **BUG-016** | Missing validation for critical Stripe config | `prep/settings.py:84,116-117` | Configuration | Medium |
| **BUG-017** | Response schema validation doesn't fail requests | `prep/api/middleware/schema_validation.py:199-204` | API Contract | Medium |

**See [`CRITICAL_BUGS_HUNTING_LIST.md`](CRITICAL_BUGS_HUNTING_LIST.md) for detailed bug hunt with reproduction steps, affected code paths, and recommended fixes.**

---

## Development Setup

### Prerequisites

- **Docker** 24+ with Docker Compose 2+
- **Python** 3.10+ (or use `pyenv` for multiple versions)
- **Node.js** 20+ and npm 10+
- **PostgreSQL** 15+ (via Docker Compose)
- **Redis** 7+ (via Docker Compose)

### Quick Bootstrap

```bash
git clone <repo-url> && cd Prep
make bootstrap      # Installs deps, starts services, runs migrations, health checks
make health         # Verify all services ready
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
cp .env.example .env.local
# Edit .env.local with your settings

# 4. Start infrastructure
docker-compose up -d postgres redis minio

# 5. Run migrations
make migrate

# 6. Start services (each in separate terminal)
# Terminal 1: API Gateway
uvicorn api.index:create_app --reload --port 8000

# Terminal 2: Node.js backend
cd prepchef && npm run dev

# Terminal 3: Frontend
cd apps/harborhomes && npm run dev
```

**Service Endpoints:**
- Frontend: `http://localhost:3001`
- API Gateway: `http://localhost:8000/docs` (OpenAPI)
- Node Backend: `http://localhost:3000/docs`
- MinIO: `http://localhost:9001`

---

## Development Workflow

### Essential Commands

```bash
make up              # Start all services
make down            # Stop all services
make test            # Run all tests (unit + integration + E2E)
make lint            # Run linters (ruff, eslint, mypy)
make format          # Auto-format code (black, prettier)
make quality-check   # Full lint + type check + security scan
make health          # Health check all services
make logs            # Tail all service logs
make db-reset        # ⚠️  Destroy and reinitialize database
```

### Database Migrations

```bash
make migrate                    # Run pending migrations
make migrate-down               # Rollback last migration
alembic revision -m "descrip"   # Create new migration
alembic downgrade -1            # Downgrade one revision
```

### Code Quality

```bash
# Individual tools
ruff check .               # Python linting
black prep/ apps/ --check  # Python formatting
mypy .                     # Python type checking
npm run lint               # TypeScript linting (prepchef)
npm run typecheck          # TypeScript type checking

# Integrated checks
make lint                  # All linters
make typecheck             # All type checkers
make format                # All formatters
pre-commit run --all-files # Pre-commit hooks
```

### Testing Commands

```bash
pytest                          # All Python tests
pytest -m integration           # Integration tests only
pytest --cov=prep              # Coverage report
cd prepchef && npm test        # Node.js tests
npm run test:e2e               # E2E tests (Playwright)
make smoke-test                # Import validation
```

### Git Workflow

```bash
git checkout -b feature/name
# ... make changes ...
make lint && make typecheck && make test
git add .
git commit -m "feat: description"
git push origin feature/name
# Create pull request
```

### Troubleshooting

See [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) for:
- Environment configuration issues
- Database connection failures
- Module import errors
- Docker networking problems
- Port conflicts
- Performance debugging

---

## Testing & Validation

### Test Coverage

| Layer | Tools | Command | Notes |
|-------|-------|---------|-------|
| **Unit** | pytest, Jest | `make test` | Fast, mocked dependencies, ~51% coverage |
| **Integration** | pytest, Supertest | `pytest -m integration` | Real DB, mocked external APIs |
| **E2E** | Playwright | `npm run test:e2e` | Full flow through all services |
| **Smoke** | Import validation | `make smoke-test` | Validates all modules load correctly |
| **Regression** | Golden-file tests | `cd regengine && pytest -v` | RIC test harness for compliance rules |
| **Load** | k6, locust | `make test:load` | Performance/scalability testing |

### CI/CD Pipeline (23 Workflows)

| Stage | Checks | Failure = Blocker |
|-------|--------|-------------------|
| **Lint** | ruff, black, eslint, prettier | ✅ Yes |
| **Type** | mypy, tsc strict mode | ✅ Yes |
| **Test** | pytest, jest, e2e | ✅ Yes |
| **Security** | gitleaks, bandit, dependabot | ✅ Yes |
| **Build** | Docker image build & scan | ✅ Yes |
| **Contract** | OpenAPI validation | ✅ Yes |

### Test Organization

```
tests/
├── unit/               # Isolated, mocked tests
├── integration/        # Real DB/Redis, mocked APIs
├── e2e/               # Full request flows
├── smoke/             # Import validation
├── perf/              # Benchmarks
├── load/              # Scalability tests
├── contract/          # API contracts
└── regression/        # Golden-file tests
```

---

## Security Architecture

### Authentication & Authorization

| Component | Implementation | Details |
|-----------|-----------------|---------|
| **Auth Flow** | JWT + Refresh Tokens | Access token: 15min, Refresh: 7 days |
| **Validation** | FastAPI security dependencies | `Depends(require_active_session)` |
| **RBAC** | Role-based access control | Roles: admin, host, renter, support |
| **Scopes** | JWT claims | Fine-grained permission checks |

### Input Validation & Sanitization

```python
# ✅ All inputs validated via Pydantic/Zod schemas
class BookingRequest(BaseModel):
    kitchen_id: UUID  # UUID not string
    duration_hours: PositiveInt  # Positive integers only
    notes: str = Field(..., max_length=500)  # Length limits

# ✅ SQL injection prevention (parameterized queries)
# ❌ Never: f"SELECT * FROM bookings WHERE id = {user_input}"
# ✅ Always: "SELECT * FROM bookings WHERE id = ?" with [user_input]
```

### Data Protection

- **Encryption at Rest**: PII fields encrypted with AES-256
- **TLS in Transit**: All external communication over HTTPS
- **Secrets Management**: AWS Secrets Manager (no hardcoded secrets)
- **Audit Logging**: All sensitive operations logged with user context

### Compliance Scanning

```bash
./verify_security.sh          # Full security audit
./security_weekly_check.sh    # Weekly automated check
./security_monthly_audit.sh   # Comprehensive monthly audit
```

**Bandit Results (Python security linting)**
- 1,632 checks run
- 0 high-severity issues
- 11 medium-severity findings (XML parsing, network binding)

### Dependency Management

- **Automated Scanning**: Dependabot pulls on security updates
- **Pre-commit Hooks**: Gitleaks scans for secrets before commit
- **GitHub Actions**: Secret scanning on every push
- **Image Scanning**: Docker image vulnerability scanning in CI/CD

---

## Operations & Monitoring

### Health Checks

```bash
make health     # Check all services
# Returns health status for: API, PostgreSQL, Redis, MinIO, Node.js services
```

### Observability

**Monitoring Stack**
- **Prometheus**: Metrics scraping (port 9090)
- **Grafana**: Dashboards and alerting (port 3000)
- **OpenTelemetry**: Distributed tracing via OTLP collector

**Key Metrics**
- `http_request_duration_seconds` – API latency
- `database_connection_pool_size` – DB connection usage
- `redis_commands_processed_total` – Cache operations
- `stripe_api_calls_total` – Payment API usage

### Deployment

**Local Development**
```bash
docker-compose up    # Start all services
```

**Production (Kubernetes)**
```bash
helm install prep ./infra/helm/prep -f values.production.yaml
kubectl logs -f deployment/prep-api-gateway
```

**Required Environment Variables**
```
DATABASE_URL=postgresql://user:pass@postgres:5432/prep
REDIS_URL=redis://redis:6379
STRIPE_SECRET_KEY=sk_live_...
JWT_SECRET_KEY=<random-256-bit-value>
ENVIRONMENT=production
```

---

## Known Technical Debt

| Item | Impact | Effort | Priority |
|------|--------|--------|----------|
| **Ruff linting errors** (974 remaining) | Code consistency | Medium | Low |
| **Type coverage** (missing stubs for third-party libs) | IDE support | High | Medium |
| **N+1 query patterns** (potential) | Performance | High | High |
| **Race condition fixes** (3 critical) | Data integrity | Medium | Critical |
| **DAG implementation** (incomplete) | ETL non-functional | High | High |
| **Test coverage** (target 85%, current 51%) | Reliability | High | Medium |
| **Audit logging robustness** | Compliance | Medium | Medium |

See [`CRITICAL_BUGS_HUNTING_LIST.md`](CRITICAL_BUGS_HUNTING_LIST.md) and [`REMAINING_ISSUES_REPORT.md`](REMAINING_ISSUES_REPORT.md).

---

## Contributing

### Setup & Branch Workflow

```bash
git clone https://github.com/PetrefiedThunder/Prep.git && cd Prep
pre-commit install                  # Install pre-commit hooks
make bootstrap                      # Setup dev environment

git checkout -b feature/your-name   # Create feature branch
# ... make changes ...
make test && make lint && make typecheck
git push origin feature/your-name   # Create pull request
```

### Code Standards

| Language | Style | Type Check | Tests |
|----------|-------|-----------|-------|
| **Python** | PEP 8 + Black | mypy strict | pytest >80% |
| **TypeScript** | Prettier | tsc --strict | jest + supertest |
| **YAML** | yamllint | - | - |
| **Docker** | hadolint | - | - |

### Commit & PR Requirements

- **Commits**: Conventional Commits format (`feat:`, `fix:`, `docs:`, etc.)
- **PR Description**: Use template in `PR_DESCRIPTION.md`
- **Tests**: All new code must have test coverage
- **CI**: All 23 workflows must pass
- **Secrets**: Never commit `.env`, credentials, or API keys

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
