# Local Development Guide

This guide covers running the Prep/PrepChef stack locally using Docker Compose.

## Prerequisites

- Docker Engine 20.10+ and Docker Compose v2+
- Git
- At least 4GB RAM available for Docker

## Services

The stack includes:
- **postgres** (port 5432): PostGIS-enabled PostgreSQL database
- **redis** (port 6379): Redis cache and session store
- **minio** (ports 9000, 9001): S3-compatible object storage
- **node-api** (port 3000): Node.js/Express API services
- **python-compliance** (port 8000): Python FastAPI compliance engine
- **frontend** (port 3001): Next.js/React frontend application

## Quick Start

### 1. Start all services

```bash
docker-compose up -d
```

This boots all services in the background. Initial startup may take 5-10 minutes to download images and build containers.

### 2. Stop all services

```bash
docker-compose down
```

To stop and remove all data volumes:

```bash
docker-compose down -v
```

### 3. Run database migrations

After first startup, apply database migrations:

```bash
docker-compose exec postgres psql -U postgres -d prepchef -f /docker-entrypoint-initdb.d/01-schema.sql
```

Or from the host (requires `psql` installed):

```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d prepchef -f migrations/init.sql
```

For incremental migrations:

```bash
docker-compose exec node-api npm run migrate
```

### 4. Seed test data

Seed the database with sample hosts, listings, and bookings:

```bash
docker-compose exec node-api npm run seed
```

Or using Python scripts:

```bash
docker-compose exec python-compliance python scripts/seed_data.py
```

### 5. Run tests

**Backend unit tests (Python):**

```bash
docker-compose exec python-compliance pytest
```

**Backend unit tests (Node.js):**

```bash
docker-compose exec node-api npm test
```

**E2E tests (Playwright):**

```bash
docker-compose exec node-api npm run test:e2e
```

### 6. View logs

**All services:**

```bash
docker-compose logs -f
```

**Specific service:**

```bash
docker-compose logs -f node-api
docker-compose logs -f python-compliance
docker-compose logs -f postgres
```

**Tail last 100 lines:**

```bash
docker-compose logs --tail=100 -f
```

## Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Key variables:
- `POSTGRES_PASSWORD`: Database password (default: `postgres`)
- `REDIS_URL`: Redis connection string
- `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`: MinIO credentials
- `STRIPE_SECRET_KEY`: Stripe API secret (use test keys for local dev)
- `JWT_SECRET`: Secret for JWT token signing

## Accessing Services

- **Frontend**: http://localhost:3001
- **Node API**: http://localhost:3000
- **Python Compliance API**: http://localhost:8000
- **MinIO Console**: http://localhost:9001 (user: minioadmin, password: minioadmin)
- **Postgres**: localhost:5432 (user: postgres, password: postgres, db: prepchef)
- **Redis**: localhost:6379

## Common Commands Summary

| Command | Description |
|---------|-------------|
| `docker-compose up -d` | Start all services in background |
| `docker-compose down` | Stop all services |
| `docker-compose exec postgres psql -U postgres -d prepchef` | Connect to database |
| `docker-compose exec node-api npm run migrate` | Run database migrations |
| `docker-compose exec node-api npm run seed` | Seed test data |
| `docker-compose exec node-api npm test` | Run Node.js tests |
| `docker-compose exec python-compliance pytest` | Run Python tests |
| `docker-compose logs -f [service]` | View service logs |
| `docker-compose restart [service]` | Restart a specific service |
| `docker-compose build --no-cache [service]` | Rebuild a service |

## Troubleshooting

**Services won't start:**
- Check Docker is running: `docker ps`
- Check logs: `docker-compose logs [service]`
- Rebuild images: `docker-compose build --no-cache`

**Port conflicts:**
- Edit `.env` to change ports
- Check what's using the port: `lsof -i :3000`

**Database connection errors:**
- Wait for postgres healthcheck: `docker-compose ps`
- Verify connection: `docker-compose exec postgres pg_isready -U postgres`

**Out of disk space:**
- Clean up: `docker system prune -a --volumes`

**Permission errors:**
- Fix volume permissions: `docker-compose exec node-api chown -R node:node /app`

## Development Workflow

1. Make code changes in your editor (changes sync via volumes)
2. Services auto-reload on file changes (node-api, python-compliance, frontend)
3. Run tests: `docker-compose exec node-api npm test`
4. View logs: `docker-compose logs -f`
5. Commit and push changes

## Resetting the Environment

To start fresh:

```bash
docker-compose down -v
docker-compose up -d
docker-compose exec node-api npm run migrate
docker-compose exec node-api npm run seed
```
