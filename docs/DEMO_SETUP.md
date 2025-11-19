# Demo Environment Setup Guide

## Overview

This guide explains how to set up and run the Prep platform in **demo mode** using mock API keys and credentials. This is perfect for:

- 🎯 **Demonstrations and presentations**
- 🧪 **Testing configuration without real API access**
- 📚 **Training and onboarding new developers**
- 🔧 **CI/CD pipelines and automated testing**
- 📖 **Documentation examples**

## ⚠️ Important Security Notice

**ALL credentials in `.env.demo` are intentionally fake and non-functional.**

- ❌ DO NOT use these in production
- ❌ DO NOT use these in development with real services
- ✅ DO use these for demos, testing, and presentations
- ✅ DO use these to validate configuration loading

## Quick Start

### 1. Copy Demo Configuration

```bash
# Copy the demo environment file
cp .env.demo .env.local

# Or create a symlink
ln -s .env.demo .env
```

### 2. Set Up Local Services

```bash
# Start PostgreSQL
# Make sure PostgreSQL is running (varies by OS)
# macOS: brew services start postgresql
# Linux: sudo systemctl start postgresql

# Create demo database
createdb prep_demo

# Start Redis
redis-server

# Optional: Start MinIO (for file storage demos)
docker run -d \
  -p 9000:9000 \
  -e "MINIO_ROOT_USER=prep_demo_minio" \
  -e "MINIO_ROOT_PASSWORD=prep_demo_minio_secret_key_2025" \
  minio/minio server /data

# Optional: Start MailHog (for email testing)
docker run -d \
  -p 1025:1025 \
  -p 8025:8025 \
  mailhog/mailhog
```

### 3. Initialize Database

```bash
# Activate virtual environment
source .venv/bin/activate

# Run migrations
alembic upgrade head

# Optional: Load demo fixtures
python -m prep.scripts.load_demo_fixtures
```

### 4. Start the Application

```bash
# Start the API server
uvicorn prep.main:app --reload --port 8000

# In another terminal, start the frontend (if applicable)
cd frontend
npm run dev
```

### 5. Access the Demo

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000 (if running)
- **MailHog UI**: http://localhost:8025 (if running)

## Mock API Keys Included

The `.env.demo` file includes realistic-looking mock keys for:

### Payment Processing
- ✅ Stripe (test mode keys)

### Authentication & Identity
- ✅ OIDC (OpenID Connect)
- ✅ SAML

### Document Management
- ✅ DocuSign

### Delivery Services
- ✅ DoorDash Drive
- ✅ Uber Direct
- ✅ Onfleet

### E-Commerce Platforms
- ✅ Shopify
- ✅ TikTok Shop

### POS Systems
- ✅ Square
- ✅ Toast
- ✅ Oracle Simphony

### Insurance Providers
- ✅ Next Insurance
- ✅ Thimble

### Cloud & Data Services
- ✅ Google Maps API
- ✅ BigQuery
- ✅ Snowflake
- ✅ Kafka

### Monitoring
- ✅ Sentry
- ✅ Datadog

## Mock Service Flags

The demo configuration enables several mock service flags to bypass real API calls:

```bash
USE_MOCK_STRIPE=true       # Mock Stripe payments
USE_MOCK_EMAIL=true        # Mock email sending
USE_MOCK_SMS=true          # Mock SMS sending
USE_MOCK_GOV_PORTALS=true  # Mock government portal integrations
USE_FIXTURES=true          # Use demo data fixtures
```

## Feature Flags

All feature flags are enabled in demo mode:

```bash
FEATURE_PILOT_PROGRAM=true
FEATURE_INSTANT_BOOKING=true
FEATURE_AI_MATCHING=true
FEATURE_DOCUMENT_OCR=true
```

## Demo User Accounts

After loading demo fixtures, you can use these test accounts:

| Role | Email | Password | Description |
|------|-------|----------|-------------|
| Admin | `admin@demo.prep` | `demo123` | Platform administrator |
| Operator | `operator@demo.prep` | `demo123` | Kitchen operator |
| Food Business | `business@demo.prep` | `demo123` | Food business owner |
| City Reviewer | `reviewer@demo.prep` | `demo123` | City compliance reviewer |

> **Note**: These are created by the demo fixtures script. See `prep/scripts/load_demo_fixtures.py`

## Testing Demo Configuration

### Verify Configuration Loading

```bash
# Test that settings load correctly
python -c "from prep.settings import get_settings; s = get_settings(); print(f'Environment: {s.environment}')"
```

Expected output:
```
Environment: demo
```

### Test Database Connection

```bash
# Run a simple database test
python -c "
from prep.db import get_session
import asyncio

async def test():
    async with get_session() as session:
        print('✅ Database connection successful')

asyncio.run(test())
"
```

### Test Redis Connection

```bash
# Test Redis
python -c "
import redis
r = redis.from_url('redis://localhost:6379/1')
r.ping()
print('✅ Redis connection successful')
"
```

## Common Demo Scenarios

### 1. Payment Flow Demo

With `USE_MOCK_STRIPE=true`, the application will simulate payment processing without calling Stripe's API:

```python
# This will work without real Stripe keys
from prep.payments import create_payment_intent

# Returns a mock payment intent
payment = await create_payment_intent(amount=5000, currency="usd")
print(payment.id)  # "pi_mock_demo_1234567890"
```

### 2. Email Notification Demo

With `USE_MOCK_EMAIL=true` and MailHog running:

```python
# Send a demo email
from prep.notifications import send_email

await send_email(
    to="demo@example.com",
    subject="Demo Email",
    body="This is a test email"
)
```

Check http://localhost:8025 to see the email in MailHog.

### 3. Document Signing Demo

With mock DocuSign credentials:

```python
# Create a demo envelope
from prep.integrations.docusign import create_envelope

envelope = await create_envelope(
    template_id="template-demo-123",
    signers=[{"email": "signer@demo.com", "name": "Demo Signer"}]
)
print(envelope.envelope_id)  # "envelope_mock_demo_123"
```

### 4. Compliance Check Demo

Test regulatory compliance checks with demo data:

```python
# Check compliance for a demo location
from prep.compliance import check_location_compliance

result = await check_location_compliance(
    zip_code="94102",  # San Francisco (pilot area)
    business_type="commercial_kitchen"
)
print(result.is_compliant)  # True (using demo data)
```

## Troubleshooting

### Database Connection Fails

```bash
# Check PostgreSQL is running
pg_isready

# Check database exists
psql -l | grep prep_demo

# Recreate database if needed
dropdb prep_demo && createdb prep_demo
alembic upgrade head
```

### Redis Connection Fails

```bash
# Check Redis is running
redis-cli ping

# Should return: PONG

# Start Redis if not running
redis-server
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

### Module Not Found Errors

```bash
# Reinstall dependencies
pip install -e .

# Or recreate virtual environment
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Resetting Demo Environment

To start fresh:

```bash
# Stop all services
# Kill uvicorn, redis-server, etc.

# Drop and recreate database
dropdb prep_demo
createdb prep_demo

# Run migrations
alembic upgrade head

# Reload fixtures
python -m prep.scripts.load_demo_fixtures

# Clear Redis
redis-cli FLUSHDB

# Restart application
uvicorn prep.main:app --reload --port 8000
```

## CI/CD Usage

For automated testing in CI/CD pipelines:

```yaml
# .github/workflows/demo-test.yml
name: Demo Environment Test

on: [push, pull_request]

jobs:
  test-demo:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: prep_demo
          POSTGRES_USER: prep_demo
          POSTGRES_PASSWORD: demo_password_2025
        ports:
          - 5432:5432

      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Copy demo config
        run: |
          cp .env.demo .env

      - name: Run migrations
        run: |
          alembic upgrade head

      - name: Load demo fixtures
        run: |
          python -m prep.scripts.load_demo_fixtures

      - name: Run tests
        run: |
          pytest tests/ -xvs

      - name: Test API startup
        run: |
          uvicorn prep.main:app --host 0.0.0.0 --port 8000 &
          sleep 5
          curl http://localhost:8000/healthz
```

## Differences from Development Environment

| Feature | Demo (`.env.demo`) | Development (`.env.development.template`) |
|---------|-------------------|------------------------------------------|
| API Keys | All fake/mock | Need real test keys |
| Mock Services | Enabled by default | Disabled (use real services) |
| Feature Flags | All enabled | Selectively enabled |
| Database | `prep_demo` | `prep_dev` |
| Purpose | Presentations, testing config | Real development work |
| Network Calls | Mocked | Hit real test APIs |

## Next Steps

- ✅ Demo configuration is ready to use
- ✅ Review `.env.demo` for all available settings
- ✅ Check `prep/settings.py` for configuration schema
- ✅ See `.claude/CONTEXT.md` for development workflows
- ✅ Read `docs/PREP_MVP_IMPLEMENTATION_PLAN.md` for architecture

## Support

For questions about demo setup:

1. Check this documentation
2. Review `.env.demo` comments
3. See `prep/settings.py` for configuration details
4. Ask in the team chat or create a GitHub issue

---

**Version**: 1.0
**Last Updated**: 2025-01-19
**Maintainer**: Christopher Sellers
**Related Files**:
- `.env.demo` - Mock configuration
- `.env.development.template` - Real development config
- `.env.example` - Minimal example
- `prep/settings.py` - Configuration schema
