#!/bin/bash
# Dev Preflight Check for Prep on Apple Silicon macOS
# Verifies all prerequisites before starting development
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FAILURES=0

echo "========================================="
echo "  Prep Development Preflight Check"
echo "========================================="
echo ""

# Helper functions
pass() {
  echo -e "${GREEN}✓${NC} $1"
}

fail() {
  echo -e "${RED}✗${NC} $1"
  FAILURES=$((FAILURES + 1))
}

warn() {
  echo -e "${YELLOW}⚠${NC} $1"
}

check_command() {
  if command -v "$1" &>/dev/null; then
    return 0
  else
    return 1
  fi
}

# 1. Check Python version (>=3.11)
echo "Checking Python..."
if check_command python3; then
  PYTHON_VERSION=$(python3 --version | awk '{print $2}')
  PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
  PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

  if [[ "$PYTHON_MAJOR" -eq 3 ]] && [[ "$PYTHON_MINOR" -ge 11 ]]; then
    pass "Python $PYTHON_VERSION (>=3.11 required)"
  else
    fail "Python $PYTHON_VERSION found, but >=3.11 required"
    echo "   Install: brew install python@3.11"
  fi
else
  fail "python3 not found"
  echo "   Install: brew install python@3.11"
fi

# 2. Check Node version (>=20.x)
echo "Checking Node.js..."
if check_command node; then
  NODE_VERSION=$(node --version | sed 's/v//')
  NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)

  if [[ "$NODE_MAJOR" -ge 20 ]]; then
    pass "Node.js $NODE_VERSION (>=20.0 required)"
  else
    fail "Node.js $NODE_VERSION found, but >=20.0 required"
    echo "   Install: brew install node@20"
  fi
else
  fail "node not found"
  echo "   Install: brew install node@20"
fi

# 3. Check npm
echo "Checking npm..."
if check_command npm; then
  NPM_VERSION=$(npm --version)
  pass "npm $NPM_VERSION"
else
  fail "npm not found (should come with Node.js)"
fi

# 4. Check pnpm (for harborhomes)
echo "Checking pnpm..."
if check_command pnpm; then
  PNPM_VERSION=$(pnpm --version)
  pass "pnpm $PNPM_VERSION"
else
  warn "pnpm not found (optional for harborhomes frontend)"
  echo "   Install: npm install -g pnpm@8.14.0"
fi

# 5. Check Docker
echo "Checking Docker..."
if check_command docker; then
  if docker info &>/dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
    pass "Docker $DOCKER_VERSION (running)"
  else
    fail "Docker installed but not running"
    echo "   Start Docker Desktop"
  fi
else
  fail "Docker not found"
  echo "   Install: brew install --cask docker"
fi

# 6. Check Docker Compose
echo "Checking Docker Compose..."
if docker compose version &>/dev/null; then
  COMPOSE_VERSION=$(docker compose version | awk '{print $4}')
  pass "Docker Compose $COMPOSE_VERSION"
else
  fail "Docker Compose not available"
  echo "   Upgrade Docker Desktop to latest version"
fi

# 7. Check required ports are free
echo "Checking required ports..."
REQUIRED_PORTS=(5432 6379 9000 9001 3000 8000)
for PORT in "${REQUIRED_PORTS[@]}"; do
  if lsof -Pi ":$PORT" -sTCP:LISTEN -t &>/dev/null; then
    PID=$(lsof -Pi ":$PORT" -sTCP:LISTEN -t)
    PROCESS=$(ps -p "$PID" -o comm= 2>/dev/null || echo "unknown")
    fail "Port $PORT is in use (PID: $PID, Process: $PROCESS)"
    echo "   Free it: lsof -ti:$PORT | xargs kill -9"
  else
    pass "Port $PORT is available"
  fi
done

# 8. Check .env file exists and has required vars
echo "Checking .env file..."
if [[ -f .env ]]; then
  pass ".env file exists"

  # Required variables
  REQUIRED_VARS=(
    "POSTGRES_URL"
    "MINIO_ENDPOINT"
    "MINIO_ACCESS_KEY"
    "MINIO_SECRET_KEY"
    "STRIPE_PUBLIC_KEY"
    "STRIPE_WEBHOOK_SECRET"
    "KMS_MASTER_KEY_HEX"
  )

  for VAR in "${REQUIRED_VARS[@]}"; do
    if grep -q "^${VAR}=" .env 2>/dev/null; then
      VALUE=$(grep "^${VAR}=" .env | cut -d= -f2)
      if [[ -z "$VALUE" ]]; then
        warn "$VAR is defined but empty in .env"
      else
        pass "$VAR is set"

        # Special checks for Stripe keys
        if [[ "$VAR" == "STRIPE_PUBLIC_KEY" ]] && [[ "$VALUE" == "pk_test_xxx" ]]; then
          warn "Using placeholder Stripe public key - update for real testing"
        fi
        if [[ "$VAR" == "STRIPE_WEBHOOK_SECRET" ]] && [[ "$VALUE" == "whsec_xxx" ]]; then
          warn "Using placeholder Stripe webhook secret - update for real testing"
        fi
      fi
    else
      fail "$VAR not found in .env"
    fi
  done
else
  fail ".env file not found"
  echo "   Copy: cp .env.example .env"
  echo "   Then edit .env with real credentials"
fi

# 9. Check Python virtual environment
echo "Checking Python environment..."
if [[ -d .venv ]]; then
  pass "Virtual environment exists (.venv)"

  # Check if venv has dependencies installed
  if [[ -f .venv/bin/python ]]; then
    if .venv/bin/python -c "import fastapi" 2>/dev/null; then
      pass "Python dependencies appear installed"
    else
      warn "Virtual environment exists but dependencies may not be installed"
      echo "   Install: source .venv/bin/activate && pip install -r requirements.txt"
    fi
  fi
else
  warn "Virtual environment not found (.venv)"
  echo "   Create: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
fi

# 10. Check Node dependencies
echo "Checking Node dependencies..."
if [[ -d prepchef/node_modules ]]; then
  pass "prepchef dependencies installed"
else
  warn "prepchef/node_modules not found"
  echo "   Install: cd prepchef && npm install"
fi

if [[ -d apps/harborhomes/node_modules ]]; then
  pass "harborhomes dependencies installed"
else
  warn "apps/harborhomes/node_modules not found"
  echo "   Install: cd apps/harborhomes && npm install"
fi

# 11. Check disk space (>=5GB)
echo "Checking disk space..."
if [[ "$(uname)" == "Darwin" ]]; then
  # macOS
  AVAILABLE_GB=$(df -g . | awk 'NR==2 {print $4}')
  if [[ "$AVAILABLE_GB" -ge 5 ]]; then
    pass "Disk space: ${AVAILABLE_GB}GB available (>=5GB required)"
  else
    fail "Only ${AVAILABLE_GB}GB available, 5GB required"
    echo "   Free up space or use a different volume"
  fi
else
  # Linux fallback
  AVAILABLE_GB=$(df -BG . | awk 'NR==2 {print $4}' | tr -d 'G')
  if [[ "$AVAILABLE_GB" -ge 5 ]]; then
    pass "Disk space: ${AVAILABLE_GB}GB available (>=5GB required)"
  else
    fail "Only ${AVAILABLE_GB}GB available, 5GB required"
  fi
fi

# 12. If Docker is running, check services connectivity
if docker info &>/dev/null && docker compose ps &>/dev/null 2>&1; then
  echo "Checking Docker services..."

  # Check if services are running
  POSTGRES_RUNNING=$(docker compose ps -q postgres 2>/dev/null)
  REDIS_RUNNING=$(docker compose ps -q redis 2>/dev/null)
  MINIO_RUNNING=$(docker compose ps -q minio 2>/dev/null)

  if [[ -n "$POSTGRES_RUNNING" ]]; then
    # Check PostgreSQL connectivity
    if docker compose exec -T postgres pg_isready -U postgres &>/dev/null; then
      pass "PostgreSQL is reachable"
    else
      warn "PostgreSQL container running but not ready"
    fi
  else
    warn "PostgreSQL container not running (run 'make up' to start)"
  fi

  if [[ -n "$REDIS_RUNNING" ]]; then
    # Check Redis connectivity
    if docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
      pass "Redis is reachable"
    else
      warn "Redis container running but not responding"
    fi
  else
    warn "Redis container not running (run 'make up' to start)"
  fi

  if [[ -n "$MINIO_RUNNING" ]]; then
    # Check MinIO connectivity
    if curl -sf http://localhost:9000/minio/health/live &>/dev/null; then
      pass "MinIO is reachable"
    else
      warn "MinIO container running but health check failed"
    fi
  else
    warn "MinIO container not running (run 'make up' to start)"
  fi
else
  warn "Docker Compose services not started yet (run 'make up' to start)"
fi

# 13. Check git repository
echo "Checking git..."
if [[ -d .git ]]; then
  pass "Git repository initialized"

  # Check if pre-commit is installed
  if check_command pre-commit; then
    pass "pre-commit is installed"

    if [[ -f .git/hooks/pre-commit ]]; then
      pass "pre-commit hooks installed"
    else
      warn "pre-commit not installed in git hooks"
      echo "   Install: pre-commit install"
    fi
  else
    warn "pre-commit not found"
    echo "   Install: pip install pre-commit && pre-commit install"
  fi
else
  fail "Not a git repository"
fi

# 14. Check for critical files
echo "Checking critical files..."
CRITICAL_FILES=(
  "requirements.txt"
  "pyproject.toml"
  "docker-compose.yml"
  "migrations/init.sql"
  "prep/main.py"
  "run_api.py"
)

for FILE in "${CRITICAL_FILES[@]}"; do
  if [[ -f "$FILE" ]]; then
    pass "$FILE exists"
  else
    fail "$FILE missing"
  fi
done

# Summary
echo ""
echo "========================================="
echo "  Summary"
echo "========================================="
if [[ $FAILURES -eq 0 ]]; then
  echo -e "${GREEN}✓ All checks passed!${NC}"
  echo ""
  echo "Next steps:"
  echo "  1. source .venv/bin/activate"
  echo "  2. make up          # Start Docker services"
  echo "  3. make migrate     # Run database migrations"
  echo "  4. make test        # Run tests"
  echo "  5. make health      # Check service health"
  echo ""
  exit 0
else
  echo -e "${RED}✗ $FAILURES check(s) failed${NC}"
  echo ""
  echo "Please fix the issues above before continuing."
  echo ""
  exit 1
fi
