# Developer Onboarding

Welcome to the Prep development team! This guide will help you set up your local environment and get started contributing.

## Prerequisites

- **Node.js** 20+ and npm
- **Python** 3.11+
- **Docker** and Docker Compose
- **PostgreSQL** 15+ client tools (psql)
- **Git**

## Local Environment Setup

### Quick Start (Recommended)

The fastest way to get started is using the Makefile:

```bash
# 1. Clone the repository
git clone [REPOSITORY_URL]
cd Prep

# 2. Bootstrap the environment (installs all dependencies)
make bootstrap

# 3. Set up your local environment
cp .env.example .env.local
# Edit .env.local with your local settings

# 4. Start all services
make up

# 5. Check database connectivity
make check-db

# 6. Run migrations
make migrate

# 7. Verify everything is working
make health
```

### Manual Setup (Alternative)

If you prefer to set up each component manually:

**1. Clone the Repository:**
```bash
git clone [REPOSITORY_URL]
cd Prep
```

**2. Install Dependencies:**

Python:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -c constraints.txt -r requirements.txt
pip install -e .
```

Node.js:
```bash
npm install
cd prepchef && npm install
cd apps/harborhomes && npm install  # If using harborhomes
```

**3. Set Up Environment Variables:**

```bash
cp .env.example .env.local
```

Edit `.env.local` and set:
- `DATABASE_URL` - Full PostgreSQL connection string (e.g., `postgresql://postgres:postgres@localhost:5432/prepchef`)
- `REDIS_URL` - Redis connection string (e.g., `redis://localhost:6379/0`)
- `STRIPE_SECRET_KEY` - Stripe test key (sk_test_...)
- `JWT_SECRET` - Random 32+ character string

Export the variables:
```bash
export $(cat .env.local | xargs)
```

**4. Validate Your Setup:**

```bash
# Check database connectivity
python scripts/check_db.py
# or
make check-db

# Test all module imports
python scripts/smoke_test_imports.py
# or
make smoke-test
```

**5. Start Services with Docker Compose:**

```bash
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- MinIO (ports 9000, 9001)
- Node API (port 3000)
- Python Compliance (port 8000)
- Frontend (port 3001)

**6. Run Database Migrations:**

```bash
make migrate
# Or manually:
docker-compose exec postgres psql -U postgres -d prepchef -f /docker-entrypoint-initdb.d/01-schema.sql
```

**7. Seed Test Data:**

```bash
npm run seed  # If available
# Or manually create test data via API
```

## Running Tests

**All Tests (Recommended):**
```bash
make test                 # Runs both Python and Node tests
```

**Python Tests:**
```bash
pytest                    # All tests
pytest tests/unit         # Unit tests only
pytest tests/integration  # Integration tests
pytest --cov=prep         # With coverage
```

**Import Smoke Tests:**
```bash
make smoke-test           # Validates all modules can be imported
python scripts/smoke_test_imports.py  # Direct script
```

**Node Tests:**
```bash
npm test                  # All tests
npm run test:unit         # Unit tests
npm run test:e2e          # E2E tests
npm run test:coverage     # With coverage
```

**E2E Tests (Playwright):**
```bash
npx playwright test
npx playwright test --ui  # Interactive mode
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Follow code style (Ruff for Python, ESLint for JS/TS)
- Write tests for new features
- Update documentation

### 3. Run Linters and Type Checking

```bash
# All linters (recommended)
make lint

# Type checking
make typecheck

# Auto-format code
make format

# Or run individually:
# Python
ruff check .
black --check .
mypy .

# Node/TypeScript
npm run lint
npm run format:check
```

### 4. Run Tests

```bash
pytest
npm test
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat: description of your changes"
```

Use conventional commits:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
# Create PR on GitHub
```

## Project Structure

```
Prep/
├── prepchef/              # Node.js microservices
│   ├── services/
│   │   ├── booking-svc/   # Booking management
│   │   ├── payments-svc/  # Stripe integration
│   │   ├── pricing-svc/   # Fee calculation
│   │   ├── compliance-svc/# Compliance checks
│   │   └── ...
│   └── packages/          # Shared packages
├── prep/                  # Python services
│   ├── compliance/        # Compliance engines
│   ├── api/              # FastAPI routes
│   └── models/           # Database models
├── apps/
│   └── web/              # Next.js frontend
├── migrations/           # Database migrations
├── scripts/              # Utility scripts
└── tests/                # Test files
```

## Common Tasks

**Check Service Health:**
```bash
make health               # Check all services
make check-db             # Check database only
```

**View Logs:**
```bash
docker-compose logs -f                    # All services
docker-compose logs -f node-api           # Specific service
```

**Restart a Service:**
```bash
docker-compose restart node-api
```

**Access Database:**
```bash
docker-compose exec postgres psql -U postgres -d prepchef
# Or from host:
psql -h localhost -U postgres -d prepchef
```

**Access Redis CLI:**
```bash
docker-compose exec redis redis-cli
```

**Run Single Microservice Locally:**
```bash
cd prepchef/services/booking-svc
npm run dev
```

**Clean Up:**
```bash
make clean                # Remove caches and temp files
make down                 # Stop all services
```

## Troubleshooting

**For comprehensive troubleshooting, see [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) which covers:**
- Missing environment variables
- Database connection failures
- Module import errors (ModuleNotFoundError, ImportError)
- Alembic migration failures
- Docker Compose issues
- Dependency conflicts
- Git/SSH issues
- And much more...

### Quick Troubleshooting

**Environment Issues:**
```bash
# Validate your setup
make check-db             # Check database connectivity
make smoke-test           # Test all module imports
make health               # Check all services

# Run pre-flight checks
bash scripts/dev_preflight.sh
```

**Docker Issues:**

Services won't start:
```bash
make down
make up
# Or fully reset:
docker-compose down -v
docker-compose up -d
```

Port conflicts:
- Edit `.env.local` to change ports
- Check: `lsof -i :3000`

Out of disk space:
```bash
make clean
docker system prune -a --volumes
```

**Database Issues:**

Connection errors:
```bash
# Run database health check
python scripts/check_db.py
# or
make check-db
```

Migrations failed:
```bash
# Reset database
docker-compose down -v
docker-compose up -d postgres
make migrate
```

**Import/Module Errors:**

Python import errors:
```bash
# Ensure editable install
pip install -e .

# Test imports
make smoke-test

# Set PYTHONPATH
export PYTHONPATH=$(pwd)
```

Node module not found:
```bash
npm install       # Reinstall dependencies
```

## Code Style Guidelines

### Python
- Use Black for formatting
- Follow PEP 8
- Max line length: 100
- Use type hints
- Docstrings for public functions

### TypeScript/JavaScript
- Use ESLint config
- Use Prettier for formatting
- Prefer async/await over promises
- Use functional components (React)

### Git Commits
- Clear, descriptive messages
- Reference issue numbers
- Squash commits before merging

## Resources

- **API Documentation**: http://localhost:3000/docs (Swagger)
- **Frontend**: http://localhost:3001
- **MinIO Console**: http://localhost:9001 (admin/minioadmin)
- **Stripe Dashboard**: https://dashboard.stripe.com/test
- **Sentry** (if configured): https://sentry.io

## Getting Help

- Slack: #prepchef-dev
- GitHub Discussions: https://github.com/PetrefiedThunder/Prep/discussions
- Email: dev@prepchef.com

## Next Steps

1. Complete this onboarding
2. Read TECHNICAL_OUTLINE.md
3. Review SECURITY.md
4. Pick a "good first issue" from GitHub
5. Join team standup (Mondays 10am)

Welcome aboard!
