.PHONY: help bootstrap up down migrate check-db smoke-test test lint typecheck health format setup policy.build opa.up db.migrate codex-verify etl.validate api.summary.test api.test api.run run-% clean preflight scan-microservices

# Default target
help:
	@echo "Prep Development Makefile"
	@echo ""
	@echo "Setup & Bootstrap:"
	@echo "  bootstrap      Install all dependencies, pre-commit hooks, and initialize dev environment"
	@echo "  preflight      Run pre-flight checks to verify environment is ready"
	@echo "  setup          Install Python dependencies only (legacy)"
	@echo ""
	@echo "Docker & Services:"
	@echo "  up             Start all Docker Compose services in background"
	@echo "  down           Stop all Docker Compose services and remove volumes"
	@echo "  migrate        Run all database migrations (SQL + Alembic)"
	@echo "  check-db       Check database connectivity and health"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  test           Run all tests (Python + Node if available)"
	@echo "  smoke-test     Run import smoke tests for all configured modules"
	@echo "  lint           Run all linters (ruff, black, bandit)"
	@echo "  typecheck      Run mypy type checking"
	@echo "  health         Check health of all running services"
	@echo "  format         Auto-format code with ruff and black"
	@echo ""
	@echo "Security:"
	@echo "  scan-microservices  Scan all Node.js microservices for security vulnerabilities"
	@echo ""
	@echo "Running Services:"
	@echo "  api.run        Run main API gateway (port 8080)"
	@echo "  run-%          Run specific service (e.g., run-compliance_service)"
	@echo ""
	@echo "Other:"
	@echo "  clean          Remove generated files, caches, and temp directories"

# Bootstrap: complete dev environment setup
bootstrap:
	@echo "🚀 Bootstrapping Prep development environment..."
	@# Check if Python 3.11+ is available
	@command -v python3 >/dev/null 2>&1 || { echo "Error: python3 not found. Install with: brew install python@3.11"; exit 1; }
	@# Create virtual environment if it doesn't exist
	@if [ ! -d .venv ]; then \
		echo "Creating Python virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@# Activate and install Python dependencies
	@echo "Installing Python dependencies..."
	@. .venv/bin/activate && \
		python -m pip install --upgrade pip --quiet && \
		pip install -r requirements.txt --quiet && \
		pip install -e . --quiet
	@# Install pre-commit
	@echo "Installing pre-commit..."
	@. .venv/bin/activate && pip install pre-commit --quiet
	@# Install git hooks
	@echo "Setting up git hooks..."
	@. .venv/bin/activate && pre-commit install
	@# Install Node dependencies for prepchef
	@if [ -d prepchef ]; then \
		echo "Installing prepchef dependencies..."; \
		cd prepchef && npm install --silent; \
	fi
	@# Install Node dependencies for harborhomes (if pnpm available, use it)
	@if [ -d apps/harborhomes ]; then \
		echo "Installing harborhomes dependencies..."; \
		if command -v pnpm >/dev/null 2>&1; then \
			cd apps/harborhomes && pnpm install --silent; \
		else \
			cd apps/harborhomes && npm install --silent; \
		fi; \
	fi
	@echo "✓ Bootstrap complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. source .venv/bin/activate"
	@echo "  2. make preflight"
	@echo "  3. make up"
	@echo "  4. make migrate"

# Preflight checks
preflight:
	@echo "Running preflight checks..."
	@bash scripts/dev_preflight.sh

# Docker Compose: start services
up:
	@echo "Starting Docker Compose services..."
	@docker compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@docker compose ps

# Docker Compose: stop services
down:
	@echo "Stopping Docker Compose services..."
	@docker compose down -v

# Database migrations
migrate:
	@echo "Running database migrations..."
	@# Wait for postgres to be ready
	@echo "Waiting for PostgreSQL to be ready..."
	@max_wait=30; \
	elapsed=0; \
	until docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; do \
		if [ "$$elapsed" -ge "$$max_wait" ]; then \
			echo "PostgreSQL not ready"; \
			exit 1; \
		fi; \
		sleep 1; \
		elapsed=$$((elapsed + 1)); \
	done
	@# Run init.sql if database is fresh
	@echo "Checking if database needs initialization..."
	@if ! docker compose exec -T postgres psql -U postgres -d prepchef -c "SELECT 1 FROM users LIMIT 1" 2>/dev/null; then \
		echo "Initializing database schema..."; \
		docker compose exec -T postgres psql -U postgres -d prepchef < migrations/init.sql; \
	else \
		echo "Database already initialized"; \
	fi
	@# Run numbered SQL migrations
	@echo "Running SQL migrations..."
	@for file in migrations/0*.sql; do \
		if [ -f "$$file" ] && [ "$$(basename $$file)" != "init.sql" ]; then \
			echo "  Applying $$(basename $$file)..."; \
			docker compose exec -T postgres psql -U postgres -d prepchef < "$$file" 2>/dev/null || true; \
		fi; \
	done
	@# Run Alembic migrations if available
	@if [ -f alembic.ini ]; then \
		echo "Running Alembic migrations..."; \
		. .venv/bin/activate && alembic upgrade head; \
	fi
	@echo "✓ Migrations complete"

# Legacy migration target (kept for compatibility)
db.migrate:
	@$(MAKE) migrate

# Database health check
check-db:
	@echo "Checking database connectivity..."
	@. .venv/bin/activate && python scripts/check_db.py

# Smoke test imports
smoke-test:
	@echo "Running import smoke tests..."
	@. .venv/bin/activate && python scripts/smoke_test_imports.py

# Run all tests
test:
	@echo "Running Python tests..."
	@. .venv/bin/activate && pytest -q || (docker compose logs python-compliance; exit 1)
	@# Run Node tests if prepchef exists
	@if [ -d prepchef ]; then \
		echo "Running prepchef tests..."; \
		cd prepchef && npm test --silent || true; \
	fi
	@# Run frontend tests if harborhomes exists
	@if [ -d apps/harborhomes ] && grep -q '"test"' apps/harborhomes/package.json; then \
		echo "Running harborhomes tests..."; \
		cd apps/harborhomes && npm test --silent || true; \
	fi

# Linting
lint:
	@echo "Running linters..."
	@. .venv/bin/activate && \
		echo "  ruff check..." && ruff check . && \
		echo "  black --check..." && black --check . --quiet && \
		echo "  bandit..." && bandit -c .bandit.yml -r prep -q || true
	@echo "✓ Linting complete"

# Type checking
typecheck:
	@echo "Running mypy type checker..."
	@. .venv/bin/activate && mypy prep apps/bookings apps/pricing --config-file mypy.ini || true
	@echo "✓ Type checking complete"

# Health checks for all services
health:
	@echo "Checking service health..."
	@echo ""
	@# Check PostgreSQL
	@printf "PostgreSQL (5432): "
	@if docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then \
		echo "✓ healthy"; \
	else \
		echo "✗ unhealthy"; \
	fi
	@# Check Redis
	@printf "Redis (6379): "
	@if docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then \
		echo "✓ healthy"; \
	else \
		echo "✗ unhealthy"; \
	fi
	@# Check MinIO
	@printf "MinIO (9000): "
	@if curl -sf http://localhost:9000/minio/health/live >/dev/null 2>&1; then \
		echo "✓ healthy"; \
	else \
		echo "✗ unhealthy"; \
	fi
	@# Check Python API
	@printf "Python API (8000): "
	@if curl -sf http://localhost:8000/healthz >/dev/null 2>&1; then \
		echo "✓ healthy"; \
		curl -sf http://localhost:8000/openapi.json >/dev/null 2>&1 && echo "  OpenAPI: ✓" || echo "  OpenAPI: ✗"; \
	else \
		echo "✗ unhealthy"; \
	fi
	@# Check Node API
	@printf "Node API (3000): "
	@if curl -sf http://localhost:3000/ >/dev/null 2>&1; then \
		echo "✓ healthy"; \
	else \
		echo "✗ unhealthy"; \
	fi
	@echo ""
	@echo "Run 'make health-verbose' for detailed health info"

# Detailed health check
health-verbose:
	@echo "Detailed service health checks..."
	@echo ""
	@echo "=== PostgreSQL ==="
	@docker compose exec -T postgres pg_isready -U postgres || true
	@echo ""
	@echo "=== Redis ==="
	@docker compose exec -T redis redis-cli ping || true
	@echo ""
	@echo "=== MinIO ==="
	@curl -s http://localhost:9000/minio/health/live || echo "MinIO not reachable"
	@echo ""
	@echo "=== Python Compliance API (8000) ==="
	@curl -s http://localhost:8000/healthz || echo "Python API not reachable"
	@echo ""
	@echo "=== Node API (3000) ==="
	@curl -s http://localhost:3000/ || echo "Node API not reachable"

# Format code
format:
	@. .venv/bin/activate && ruff format .

# Legacy setup target (kept for compatibility)
setup:
	@python -m pip install --upgrade pip
	@pip install -r requirements.txt
	@pip install pytest requests pydantic sqlalchemy psycopg2-binary opentelemetry-sdk

# Run specific service (e.g., make run-federal_regulatory_service)
run-%:
	@. .venv/bin/activate && uvicorn apps.$*/main:app --reload

# Run main API gateway
api.run:
	@. .venv/bin/activate && uvicorn run_api:app --host 0.0.0.0 --port 8080 --reload

# Legacy targets (kept for compatibility)
policy.build:
	@python apps/policy/compile.py

opa.up:
	@docker run --rm -d --name prep-opa -p 8181:8181 -v "$(PWD)/apps/policy/bundles:/policy" openpolicyagent/opa:latest run --server /policy

codex-verify:
	@python codex/eval/verify_readiness.py

etl.validate:
	@python tools/fee_validate.py

api.summary.test:
	@. .venv/bin/activate && pytest -q tests/api/test_city_fees_summary.py

api.test:
	@. .venv/bin/activate && pytest -q tests/api/test_city_fees.py

# Scan microservices for security vulnerabilities
scan-microservices:
	@echo "Scanning microservices for security vulnerabilities..."
	@bash scripts/scan_microservices.sh

# Clean up generated files
clean:
	@echo "Cleaning up..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	@rm -rf dist/ build/ .coverage htmlcov/ scan-results/ 2>/dev/null || true
	@echo "✓ Cleanup complete"
