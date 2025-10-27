# Developer Onboarding (J31)

Welcome to the PrepChef development team! This guide will help you set up your local environment and get started contributing.

## Prerequisites

- **Node.js** 20+ and npm
- **Python** 3.11+
- **Docker** and Docker Compose
- **PostgreSQL** 15+ client tools (psql)
- **Git**

## Local Environment Setup

### 1. Clone the Repository

```bash
git clone https://github.com/PetrefiedThunder/Prep.git
cd Prep
```

### 2. Install Dependencies

**Python:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

**Node.js:**
```bash
npm install
cd prepchef && npm install
```

### 3. Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and set:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `STRIPE_SECRET_KEY` - Stripe test key (sk_test_...)
- `JWT_SECRET` - Random 32+ character string

### 4. Start Services with Docker Compose

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

### 5. Run Database Migrations

```bash
docker-compose exec postgres psql -U postgres -d prepchef -f /docker-entrypoint-initdb.d/01-schema.sql
# Or manually:
psql -h localhost -U postgres -d prepchef -f migrations/init.sql
```

### 6. Seed Test Data

```bash
npm run seed  # If available
# Or manually create test data via API
```

## Running Tests

**Python Tests:**
```bash
pytest                    # All tests
pytest tests/unit         # Unit tests only
pytest tests/integration  # Integration tests
pytest --cov=prep         # With coverage
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

### 3. Run Linters

```bash
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

## Troubleshooting

### Docker Issues

**Services won't start:**
```bash
docker-compose down -v
docker-compose up -d
```

**Port conflicts:**
- Edit `.env` to change ports
- Check: `lsof -i :3000`

**Out of disk space:**
```bash
docker system prune -a --volumes
```

### Database Issues

**Migrations failed:**
```bash
# Reset database
docker-compose down -v
docker-compose up -d postgres
# Re-run migrations
```

**Connection refused:**
- Ensure Postgres is running: `docker-compose ps`
- Check DATABASE_URL in `.env`

### Test Failures

**Import errors (Python):**
```bash
pip install -e .  # Reinstall in editable mode
```

**Module not found (Node):**
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
