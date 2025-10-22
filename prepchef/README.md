# PrepChef Backend

Commercial kitchen rental marketplace API built with Fastify, Prisma, and PostgreSQL.

## Quick Start

### Prerequisites
- Node.js 20+
- Docker & Docker Compose
- npm or yarn

### Local Development Setup

1. **Start infrastructure services**:
```bash
# From project root
docker-compose up -d

# Check services are running
docker-compose ps

# View logs
docker-compose logs -f
```

This starts:
- PostgreSQL 15 with PostGIS (port 5432)
- Redis 7 (port 6379)
- MinIO (S3-compatible storage) (ports 9000, 9001)
- MailHog (email testing) (ports 1025, 8025)

2. **Install dependencies**:
```bash
cd prepchef
npm install
```

3. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your values (DATABASE_URL, JWT_SECRET, etc.)
```

4. **Run database migrations**:
```bash
# Generate Prisma client
npx prisma generate

# Apply schema (first time only)
npx prisma db push

# Or use migrations for production
npx prisma migrate dev --name init
```

5. **Start development server**:
```bash
# Start all services (from prepchef/)
npm run dev

# Or start specific service
npm run dev -w services/auth-svc
npm run dev -w services/booking-svc
```

### Accessing Services

| Service | URL | Credentials |
|---------|-----|-------------|
| **API** | http://localhost:3000 | - |
| **PostgreSQL** | localhost:5432 | postgres / postgres |
| **Redis** | localhost:6379 | - |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin |
| **MailHog UI** | http://localhost:8025 | - |
| **pgAdmin** | http://localhost:5050 | admin@prepchef.com / admin |

### Database Management

```bash
# View database schema in browser
npx prisma studio

# Create migration
npx prisma migrate dev --name description

# Reset database (dev only!)
npx prisma migrate reset

# Generate Prisma client after schema changes
npx prisma generate

# Seed database (TODO: create seed script)
npx prisma db seed
```

## Project Structure

```
prepchef/
├── prisma/
│   └── schema.prisma          # Prisma ORM schema
├── packages/
│   ├── common/                # Shared types & utilities
│   ├── logger/                # Logging package
│   └── generated/             # Generated OpenAPI types
├── services/
│   ├── api-svc/               # Main API gateway (monolith for MVP)
│   ├── auth-svc/              # Authentication service
│   ├── booking-svc/           # Booking management
│   ├── listing-svc/           # Kitchen listings
│   ├── payments-svc/          # Stripe integration
│   ├── compliance-svc/        # Document verification
│   ├── availability-svc/      # Calendar management
│   ├── notif-svc/             # Notifications (email/SMS)
│   └── admin-svc/             # Admin operations
└── tests/
    ├── e2e/                   # End-to-end tests
    └── integration/           # Integration tests
```

## Architecture

### Current: Microservices (11 services)
Each service runs independently on random ports (3000-4000 range).

### MVP Recommendation: Monolith
Consolidate services into single API gateway at `services/api-svc` for:
- Faster development velocity
- Simpler deployment (one Docker container)
- Easier debugging and testing
- Lower infrastructure costs

See [MVP Implementation Plan](../docs/PREP_MVP_IMPLEMENTATION_PLAN.md) for detailed architecture decisions.

## Testing

```bash
# Run all tests
npm run test

# Run tests with coverage
npm run test -- --coverage

# Run specific service tests
npm run test -w services/auth-svc

# E2E tests (requires services running)
npm run test:e2e
```

## Building for Production

```bash
# Build all services
npm run build

# Lint code
npm run lint

# Type check
npx tsc --noEmit
```

## Common Tasks

### Adding a new service

```bash
mkdir -p services/new-svc/src
cd services/new-svc
npm init -y
npm install fastify @fastify/cors @prep/logger @prep/common
```

### Adding a new table

1. Update `prisma/schema.prisma`
2. Create migration: `npx prisma migrate dev --name add_table_name`
3. Generate client: `npx prisma generate`
4. Add types to `packages/common/src/types.ts`

### Environment Variables

Required environment variables (see `.env.example`):

**Core**:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `JWT_SECRET` - JWT signing secret
- `NODE_ENV` - Environment (development/production)

**Third-Party Services**:
- `STRIPE_SECRET_KEY` - Stripe API key
- `RESEND_API_KEY` - Email service API key
- `SUPABASE_URL` - File storage URL
- `GOOGLE_MAPS_API_KEY` - Maps API key

## Troubleshooting

### Database connection issues
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres

# Test connection
psql postgresql://postgres:postgres@localhost:5432/prepchef
```

### Prisma client out of sync
```bash
# Regenerate Prisma client
npx prisma generate

# If schema differs from database
npx prisma db pull
npx prisma generate
```

### Port conflicts
```bash
# Check what's using port 5432
lsof -i :5432

# Stop all containers
docker-compose down

# Start with fresh volumes
docker-compose down -v
docker-compose up -d
```

## Production Deployment

### Environment Setup
1. Create Supabase project for PostgreSQL + Storage
2. Create Upstash Redis instance (or Supabase Redis)
3. Set up Stripe account (Connect enabled)
4. Configure Resend for email
5. Set all environment variables in Fly.io secrets

### Deploy to Fly.io
```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Create app
fly launch

# Set secrets
fly secrets set DATABASE_URL="postgresql://..."
fly secrets set JWT_SECRET="..."
fly secrets set STRIPE_SECRET_KEY="..."
fly secrets set RESEND_API_KEY="..."

# Deploy
fly deploy
```

## Development Workflow

1. **Create feature branch**: `git checkout -b feature/my-feature`
2. **Make changes**: Implement your feature
3. **Run tests**: `npm run test`
4. **Commit**: `git commit -m "feat: add my feature"`
5. **Push**: `git push origin feature/my-feature`
6. **Create PR**: GitHub will show CI status

## Resources

- [Prisma Documentation](https://www.prisma.io/docs)
- [Fastify Documentation](https://www.fastify.io/docs)
- [Technical Outline](../TECHNICAL_OUTLINE.md)
- [MVP Implementation Plan](../docs/PREP_MVP_IMPLEMENTATION_PLAN.md)
- [Engineering Plan](../docs/prepchef_mvp_engineering_plan.md)
- [Gap Analysis](../docs/prep_mvp_gap_analysis.md)

## Services Overview

### auth-svc (Week 1-2)
Authentication, registration, JWT tokens, email verification

### listing-svc (Week 3)
Kitchen CRUD, photo upload, search, geospatial queries

### compliance-svc (Week 4)
Document upload, admin review, expiry tracking

### availability-svc (Week 5)
Calendar management, recurring schedules, Redis caching

### booking-svc (Week 7)
Booking creation, conflict detection, status workflow

### payments-svc (Week 7, 9)
Stripe integration, payment intents, Connect payouts

### notif-svc (Week 7)
Email (Resend), SMS (Twilio), push notifications

### admin-svc (Week 4, 10)
Certification approval, user moderation, analytics

## Support

For issues or questions:
1. Check [Implementation Plan](../docs/PREP_MVP_IMPLEMENTATION_PLAN.md)
2. Review [Gap Analysis](../docs/prep_mvp_gap_analysis.md)
3. Read [Engineering Plan](../docs/prepchef_mvp_engineering_plan.md)
4. Open GitHub issue
