# Prep Development Troubleshooting Guide

This guide helps you quickly diagnose and fix common development issues in the Prep codebase.

## Quick Fixes for Common Issues

### 1. Missing Environment Variables

**Symptom:** Services crash on startup with `KeyError`, `None` values, or "environment variable not set" errors.

**Root Cause:** No `.env` file or missing required variables.

**Fix:**
```bash
# Copy the local development template
cp .env.example .env.local

# Edit values if needed
vim .env.local

# Export variables for current shell
export $(cat .env.local | xargs)

# Or use in docker-compose
docker compose --env-file .env.local up
```

**Required variables:**
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` - Object storage

### 2. Database Connection Failures

**Symptom:** `could not connect to server`, `FATAL: database "prepchef" does not exist`, or migration errors.

**Root Cause:** PostgreSQL not running or database not initialized.

**Fix:**
```bash
# Start database services
make up

# Wait for healthy status
docker compose ps

# Check database connectivity
python scripts/check_db.py

# Run migrations
make migrate
```

**Advanced debugging:**
```bash
# Check if postgres is running
docker compose ps postgres

# View postgres logs
docker compose logs postgres

# Connect manually to test
psql "postgresql://postgres:postgres@localhost:5432/prepchef"
```

### 3. ModuleNotFoundError / ImportError

**Symptom:** `ModuleNotFoundError: No module named 'api'`, `ImportError: cannot import name 'X'`.

**Root Cause:** PYTHONPATH not set or package not installed in editable mode.

**Fix:**
```bash
# Install package in editable mode
pip install -e .

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Verify import works
python -c "import api; import prep; print('Imports OK')"
```

**For specific module errors:**
```bash
# Check if module file exists
find . -name "module_name.py"

# Verify __init__.py files in parent packages
ls -la api/__init__.py prep/__init__.py

# Try importing with better error messages
python -c "from libs.safe_import import safe_import; safe_import('your.module')"
```

### 4. Alembic Migration Failures

**Symptom:** `alembic upgrade head` fails with connection or SQL errors.

**Root Cause:** Database not running, DATABASE_URL not set, or migration conflicts.

**Fix:**
```bash
# 1. Verify DATABASE_URL is set
echo $DATABASE_URL
# Should output: postgresql://postgres:postgres@localhost:5432/prepchef

# 2. Check database is healthy
python scripts/check_db.py

# 3. Check current migration status
alembic current

# 4. Try running migrations
alembic upgrade head

# If migrations fail with SQL errors, check logs
docker compose logs postgres
```

**Rollback if needed:**
```bash
# Rollback one revision
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# View history
alembic history
```

### 5. Docker Compose Issues

**Symptom:** `service "X" not found`, build failures, or container crashes.

**Root Cause:** Missing build args, outdated images, or port conflicts.

**Fix:**
```bash
# Rebuild all services
docker compose build --no-cache

# Stop and remove all containers/volumes
make down

# Start fresh
make up

# Check service health
make health

# View logs for specific service
docker compose logs -f python-compliance
```

**Port conflicts:**
```bash
# Check what's using port 5432 (postgres)
lsof -i :5432

# Use different ports in .env.local
echo "POSTGRES_PORT=5433" >> .env.local
```

### 6. Dynamic Import Failures

**Symptom:** Errors from `importlib.import_module()`, plugin systems failing.

**Root Cause:** Module path incorrect, module has errors, or dependencies missing.

**Fix:**

The codebase now uses `libs.safe_import.safe_import()` which provides better error messages:

```python
# Instead of:
# module = importlib.import_module(module_str)

# Use:
from libs.safe_import import safe_import
module = safe_import(module_str, optional=True)
```

**Check module is valid:**
```bash
# Test import with clear errors
python << 'PY'
from libs.safe_import import safe_import
safe_import("api.routes.city_fees")
PY
```

### 7. Dependency Version Conflicts

**Symptom:** `ImportError`, `TypeError`, or `AttributeError` from third-party packages.

**Root Cause:** Incompatible package versions or missing dependencies.

**Fix:**
```bash
# Reinstall all dependencies
pip install -c constraints.txt -r requirements.txt --force-reinstall

# Or use fresh virtual environment
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -c constraints.txt -r requirements.txt
pip install -e ".[dev]"
```

**Check specific package:**
```bash
# Show installed version
pip show sqlalchemy

# Check for conflicts
pip check
```

### 8. Git / SSH Passphrase Blocking

**Symptom:** Scripts hang waiting for passphrase, submodule operations block.

**Root Cause:** SSH key requires passphrase but no agent running.

**Fix:**
```bash
# Start ssh-agent and add key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Or use HTTPS with PAT
git config --global url."https://github.com/".insteadOf "git@github.com:"

# For CI/automation, use deploy keys or GitHub tokens
```

### 9. Test Failures

**Symptom:** Pytest failures, import errors in tests, or database errors.

**Root Cause:** Test dependencies missing, database not seeded, or env vars not set.

**Fix:**
```bash
# Install test dependencies
pip install -e ".[dev]"

# Set test environment variables
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/prepchef_test"

# Run database for tests
make up

# Run tests with verbose output
pytest -vv

# Run specific test file
pytest tests/api/test_city_fees.py -v
```

### 10. Slow / Missing Observability

**Symptom:** Errors are swallowed, no logs, hard to debug.

**Root Cause:** Logging not configured or errors caught without logging.

**Fix:**

Configure logging in your entrypoint:
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

Use the safe_import helper which includes automatic logging:
```python
from libs.safe_import import safe_import
# Automatically logs errors with context
module = safe_import("your.module", optional=True)
```

## Pre-flight Checklist

Before starting development, run:

```bash
# 1. Bootstrap environment
make bootstrap

# 2. Verify environment is ready
make preflight

# 3. Start services
make up

# 4. Check service health
make health

# 5. Run migrations
make migrate

# 6. Run tests
make test
```

## Common Commands

```bash
# Full clean and restart
make clean down
make bootstrap
make up
make migrate

# Quick restart
make down && make up

# View all service logs
docker compose logs -f

# Check database
python scripts/check_db.py

# Lint code
make lint

# Format code
make format

# Type check
make typecheck
```

## Getting Help

1. Check this troubleshooting guide
2. Review `DEVELOPER_ONBOARDING.md` for setup instructions
3. Check `README.local.md` for local development guide
4. Run `make help` for available commands
5. Check service health: `make health`
6. View docker logs: `docker compose logs <service>`

## Reporting Issues

If you encounter an issue not covered here:

1. Collect diagnostic info:
   ```bash
   # System info
   python --version
   docker --version
   docker compose version

   # Service status
   docker compose ps

   # Recent logs
   docker compose logs --tail=100

   # Environment (scrub secrets!)
   env | grep -E '(DATABASE|REDIS|PYTHON)' | sed 's/=.*/=***/'
   ```

2. Create an issue with:
   - Error message and full stack trace
   - Steps to reproduce
   - Environment info from above
   - What you've already tried

## Advanced Debugging

### Enable SQL Echo
```bash
export SQLA_ECHO=true
```

### Debug Alembic
```bash
# Verbose alembic output
alembic -v upgrade head
```

### Debug Docker Build
```bash
# Build with verbose output
docker compose build --progress=plain python-compliance
```

### Python Debugger
```python
# Add breakpoint in code
breakpoint()  # Python 3.7+

# Or use pdb
import pdb; pdb.set_trace()
```

### Network Debugging
```bash
# Check service connectivity from container
docker compose exec python-compliance ping postgres
docker compose exec python-compliance nc -zv postgres 5432
```
