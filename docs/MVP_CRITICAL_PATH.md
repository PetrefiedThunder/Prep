# MVP Critical Path - Phase 0 Through Launch

**Created**: 2025-11-30
**Deadline**: December 7, 2025, 11:59 PM PT
**Status**: 🚨 PHASE 0 - ARCHITECTURE RESET REQUIRED

---

## ⚠️ CRITICAL REALITY CHECK

**SYSTEM_PROMPT.md is NON-NEGOTIABLE**: The MVP must use ONLY 3 core services:
1. **FastAPI API Gateway** (Python) - `api/`
2. **Next.js Frontend** (TypeScript) - `apps/harborhomes/`
3. **Postgres + Redis** (Docker) - Infrastructure only

**Current State**: We have 6+ TypeScript microservices (`prepchef/services/`) that violate this constraint.

**Phase 0 Mission**: Consolidate ALL backend logic into the FastAPI gateway before proceeding with MVP features.

---

## Phase 0: Architecture Consolidation (CURRENT PHASE)

**Duration**: 2-3 days
**Blocking**: ALL other work
**Priority**: 🔴 P0 - CRITICAL

### Objective

Migrate all working backend logic from TypeScript microservices into the existing FastAPI gateway (`api/`) to comply with the 3-service architecture mandate.

### Current Service Inventory

#### TypeScript Services (TO BE CONSOLIDATED)
- ✅ `auth-svc` - User registration, login, JWT tokens (Prisma + bcrypt)
- ✅ `listing-svc` - Kitchen listing CRUD with search (Prisma)
- ✅ `booking-svc` - Booking creation, conflict detection, pricing (Prisma)
- ✅ `payments-svc` - Stripe PaymentIntent, webhooks (Real Stripe SDK + Prisma)
- ⚠️ `availability-svc` - Availability windows (Prisma, partially complete)
- ⚠️ `notif-svc` - Notifications (stub only)

#### FastAPI Gateway (TARGET)
- **Location**: `api/index.py` (main entry point)
- **Shared Libraries**: `prep/` (auth, models, payments, compliance)
- **Database**: SQLAlchemy async + Alembic migrations
- **Current State**: Has some endpoints, but NOT the MVP critical path

### Consolidation Strategy

#### Step 1: Audit What Works (1 day)

**Task 0.1**: Map working TS service endpoints to Python equivalents
- Document what auth-svc, listing-svc, booking-svc, payments-svc do
- Identify which `prep/` modules already have equivalent logic
- Find gaps where TS has features Python doesn't

**Task 0.2**: Check FastAPI gateway structure
- Read `api/index.py` and all routes
- Review `prep/models/` SQLAlchemy models vs. Prisma schema
- Verify database migrations are current (`alembic/versions/`)

**Task 0.3**: Test existing FastAPI endpoints
```bash
cd /home/user/Prep
source .venv/bin/activate
uvicorn api.index:app --reload --port 8000
curl http://localhost:8000/docs  # Check what exists
```

#### Step 2: Port MVP Critical Endpoints (1-2 days)

**Priority Order** (implement in this sequence):

##### 2A. Auth Endpoints (4 hours)
**From**: `prepchef/services/auth-svc/src/api/auth.ts`
**To**: `api/routes/auth.py` (or similar)

Implement:
- `POST /api/v1/auth/register` - User registration
  - Validate email/password (Pydantic)
  - Hash password (bcrypt via `prep.auth.core`)
  - Create User record (SQLAlchemy)
  - Return JWT token

- `POST /api/v1/auth/login` - User login
  - Validate credentials
  - Return JWT + refresh token

- `POST /api/v1/auth/refresh` - Refresh token
  - Validate refresh token
  - Return new access token

**Reuse**: `prep/auth/core.py` (JWT helpers already exist)

##### 2B. Listing Endpoints (4 hours)
**From**: `prepchef/services/listing-svc/src/api/listings.ts`
**To**: `api/routes/listings.py`

Implement:
- `GET /api/v1/listings` - Search listings
  - Query params: `min_price`, `max_price`, `limit`, `offset`
  - SQLAlchemy query with filters
  - Return paginated results

- `GET /api/v1/listings/{id}` - Get listing details
  - Include venue, business, availability windows, reviews

- `POST /api/v1/listings` - Create listing (host only)
  - Requires authentication
  - Validate input (Pydantic schema)

**Reuse**: `prep/models/orm.py` (KitchenListing, Venue models exist)

##### 2C. Booking Endpoints (6 hours)
**From**: `prepchef/services/booking-svc/src/api/bookings.ts`
**To**: `api/routes/bookings.py`

Implement:
- `POST /api/v1/bookings` - Create booking
  - Validate listing exists and is active
  - Check for time conflicts (SQLAlchemy query)
  - Calculate pricing (hourly rate + fees + tax)
  - Create Booking record
  - Return booking ID + total

- `GET /api/v1/bookings/{id}` - Get booking details

- `POST /api/v1/bookings/{id}/confirm` - Prepare for payment
  - Call Stripe via `prep.payments.stripe_client`
  - Return client_secret

**Reuse**:
- `prep/models/orm.py` (Booking model)
- `prep/pricing/` (if exists, or implement inline)

##### 2D. Payment Endpoints (6 hours)
**From**: `prepchef/services/payments-svc/src/index.ts`
**To**: `api/routes/payments.py`

Implement:
- `POST /api/v1/payments/intents` - Create PaymentIntent
  - Validate booking exists
  - Call Stripe SDK (via `prep.payments.stripe_client`)
  - Store payment_intent_id in booking
  - Return client_secret

- `POST /api/v1/payments/webhook` - Stripe webhook handler
  - Verify signature
  - Handle `payment_intent.succeeded`
  - Update booking status to 'confirmed'
  - Idempotency via database table

**Reuse**: `prep/payments/stripe_client.py` (check if exists, or create)

#### Step 3: Database Schema Alignment (2 hours)

**Task 0.4**: Ensure SQLAlchemy models match Prisma schema
- Compare `prepchef/prisma/schema.prisma` with `prep/models/orm.py`
- Add missing fields to SQLAlchemy models
- Create Alembic migration for new fields

**Task 0.5**: Add missing tables
- `stripe_webhook_events` (for idempotency)
- Any other tables Prisma has that SQLAlchemy doesn't

```bash
cd /home/user/Prep
alembic revision --autogenerate -m "align schema with prisma for mvp"
alembic upgrade head
```

#### Step 4: Verification (2 hours)

**Task 0.6**: Manual test the consolidated flow
```bash
# Start FastAPI only (no TS services)
uvicorn api.index:app --reload --port 8000

# Test each endpoint
curl -X POST http://localhost:8000/api/v1/auth/register ...
curl http://localhost:8000/api/v1/listings ...
curl -X POST http://localhost:8000/api/v1/bookings ...
curl -X POST http://localhost:8000/api/v1/payments/intents ...
```

**Task 0.7**: Update tests
- Port key tests from TS to Python (pytest)
- Focus on critical path only (not 100% coverage yet)

### Deliverables (Phase 0 Complete)

- [ ] All 4 endpoint groups working in FastAPI
- [ ] Zero dependency on TypeScript services for MVP happy path
- [ ] Database migrations current and applied
- [ ] Manual smoke test passes (registration → booking → payment)
- [ ] Documentation: `docs/PHASE_0_CONSOLIDATION.md` with before/after

### Exit Criteria

**Phase 0 is COMPLETE when**:
1. You can run ONLY FastAPI + Next.js + Docker (Postgres/Redis)
2. The MVP happy path works without starting any TS services
3. All TS service code is marked as `POST-MVP` or deleted

---

## Phase 1: Wire Frontend to Real Backend (3-4 days)

**Depends On**: Phase 0 complete
**Focus**: Replace ALL mock data in `apps/harborhomes/` with real API calls

### Tasks

#### 1.1: Auth Flow (1 day)
- Replace mock signup with `POST /api/v1/auth/register`
- Replace mock login with `POST /api/v1/auth/login`
- Store JWT in localStorage/cookies
- Add protected route wrapper

#### 1.2: Listing Flow (1 day)
- Replace mock listings with `GET /api/v1/listings`
- Replace mock detail page with `GET /api/v1/listings/{id}`
- Wire search filters to query params

#### 1.3: Booking Flow (1 day)
- Replace mock booking with `POST /api/v1/bookings`
- Show real pricing breakdown from API response
- Handle conflict errors (show user-friendly message)

#### 1.4: Payment Flow (1 day)
- Integrate Stripe Elements (React)
- Call `POST /api/v1/bookings/{id}/confirm` to get client_secret
- Use `@stripe/stripe-js` to confirm payment
- Show confirmation page on success

### Deliverables

- [ ] End-to-end flow works in browser
- [ ] No console errors or 404s
- [ ] User can complete signup → search → book → pay
- [ ] Receipt page shows real data from database

---

## Phase 2: Stripe Production Integration (2 days)

**Depends On**: Phase 1 complete
**Focus**: Make payments REAL (test mode → production ready)

### Tasks

#### 2.1: Stripe Webhook Setup (4 hours)
- Deploy webhook endpoint to accessible URL (ngrok for local, or staging)
- Configure webhook in Stripe Dashboard
- Test webhook delivery with `stripe trigger`

#### 2.2: Payment Confirmation Loop (4 hours)
- Ensure webhook updates booking status
- Add polling in frontend to detect status change
- Show success message when booking confirmed

#### 2.3: Error Handling (4 hours)
- Handle payment failures gracefully
- Allow retry on failed payment
- Show clear error messages (no raw Stripe errors)

### Deliverables

- [ ] Webhook processes events successfully (check Stripe dashboard)
- [ ] Booking status updates to 'confirmed' after payment
- [ ] User sees confirmation within 3 seconds
- [ ] Failed payments show retry option

---

## Phase 3: Testing & Polish (2 days)

**Depends On**: Phase 2 complete
**Focus**: Ensure reliability and coverage

### Tasks

#### 3.1: E2E Playwright Test (1 day)
- Write `tests/e2e/mvp-happy-path.spec.ts`
- Test: Register → Search → Book → Pay → Confirm
- Use Stripe test card `4242 4242 4242 4242`
- Assert booking status = 'confirmed' at end

#### 3.2: Backend Unit Tests (4 hours)
- Test auth endpoints (registration, login)
- Test booking conflict detection
- Test payment intent creation
- Target: 55%+ overall coverage (100% for security-critical)

#### 3.3: Manual QA (4 hours)
- Test on different browsers (Chrome, Firefox, Safari)
- Test mobile responsive design
- Test error cases (invalid card, expired session, etc.)
- Fix any bugs found

### Deliverables

- [ ] Playwright test passes in CI
- [ ] Coverage report shows ≥55% overall, 100% for auth/payments
- [ ] Manual test checklist 100% passed
- [ ] Zero critical bugs remaining

---

## Phase 4: Launch Prep (1-2 days)

**Depends On**: Phase 3 complete
**Focus**: Production readiness

### Tasks

#### 4.1: Deployment (4 hours)
- Configure production environment variables
- Deploy FastAPI to hosting (Railway, Fly.io, or AWS)
- Deploy Next.js to Vercel
- Set up Postgres on managed service (Supabase, Neon, or RDS)

#### 4.2: Monitoring (2 hours)
- Add Sentry for error tracking
- Set up basic logging (structured JSON)
- Configure alerts for payment failures

#### 4.3: Documentation (2 hours)
- Update README with production setup
- Document environment variables
- Create demo video (2-3 minutes)

### Deliverables

- [ ] MVP deployed and accessible via public URL
- [ ] Monitoring and alerts active
- [ ] Demo video recorded
- [ ] Non-founder can test the flow

---

## Timeline Summary

| Phase | Duration | Completion Date |
|-------|----------|-----------------|
| **Phase 0**: Architecture Consolidation | 2-3 days | Dec 3, 2025 |
| **Phase 1**: Frontend Integration | 3-4 days | Dec 6, 2025 |
| **Phase 2**: Stripe Integration | 2 days | Overlap with Phase 1 |
| **Phase 3**: Testing & Polish | 2 days | Dec 7, 2025 (AM) |
| **Phase 4**: Launch Prep | 1 day | Dec 7, 2025 (PM) |

**CRITICAL**: We have 7 days remaining. Phase 0 MUST complete by Dec 3 to stay on track.

---

## Risk Mitigation

### Risk: Phase 0 takes longer than 3 days
**Mitigation**:
- Only port endpoints needed for MVP happy path (ignore admin, analytics, etc.)
- Reuse existing `prep/` modules aggressively
- Skip tests initially, add in Phase 3

### Risk: FastAPI gateway missing critical features
**Mitigation**:
- Audit existing `prep/` modules FIRST (they may already have what we need)
- Copy TS logic directly if needed (translate, don't redesign)

### Risk: Database schema conflicts between Prisma and SQLAlchemy
**Mitigation**:
- Use Prisma schema as source of truth
- Generate Alembic migration to match
- Test migration on clean database

### Risk: Stripe webhook failures in production
**Mitigation**:
- Implement retry queue (using Redis)
- Add idempotency check (database table)
- Monitor webhook delivery in Stripe dashboard

---

## Success Metrics (MVP Launch)

**Technical**:
- ✅ Zero TypeScript services running in production
- ✅ E2E test passes at 95%+ success rate
- ✅ Test coverage ≥55% overall, 100% for auth/payments/booking
- ✅ API latency p95 < 500ms
- ✅ Webhook processing < 2 seconds

**Business**:
- ✅ Non-founder completes booking in < 5 minutes
- ✅ Payment success rate ≥99% (Stripe test mode)
- ✅ Zero manual steps required
- ✅ Receipt shows correct pricing and booking details

---

## Phase 0 Action Plan (START HERE)

### Today (Day 1)
1. ✅ Read SYSTEM_PROMPT.md, CONTEXT.md, MVP_CRITICAL_PATH.md
2. Audit `api/index.py` and all routes
3. Audit `prep/` modules (auth, models, payments)
4. Map TS endpoints → Python equivalents (create spreadsheet)
5. Identify gaps and estimate effort

### Tomorrow (Day 2)
6. Implement auth endpoints in FastAPI
7. Implement listing endpoints in FastAPI
8. Create Alembic migration for any missing fields
9. Test manually with curl

### Day 3
10. Implement booking endpoints in FastAPI
11. Implement payment endpoints in FastAPI
12. Test end-to-end flow (FastAPI only, no TS services)
13. Document completion in `docs/PHASE_0_CONSOLIDATION.md`

---

## Questions to Resolve (Phase 0)

- [ ] Does `prep/payments/stripe_client.py` exist? If not, create it.
- [ ] Does `prep/pricing/` have pricing calculation logic? If not, port from TS.
- [ ] Are SQLAlchemy models current with latest business requirements?
- [ ] Do we have Redis configured for booking locks and webhook idempotency?

---

## POST-MVP Work (Explicitly Deferred)

The following are OUT OF SCOPE for Dec 7 MVP:
- ❌ Admin certification queue
- ❌ File upload (photos, documents)
- ❌ Email notifications (Resend/SendGrid)
- ❌ Advanced search (PostGIS, Elasticsearch)
- ❌ Cancellation and refund flow
- ❌ Reviews and ratings
- ❌ Messaging between host/vendor
- ❌ Multi-region Stripe support
- ❌ Advanced analytics and reporting

These are valuable but DO NOT BLOCK the MVP happy path.

---

## Commit Strategy

- **Phase 0**: Commit per endpoint group (auth, listings, bookings, payments)
- **Phase 1**: Commit per page (signup, search, booking, checkout)
- **Phase 2**: Commit after webhook integration works
- **Phase 3**: Commit after E2E test passes
- **Phase 4**: Commit after deployment succeeds

All commits should follow:
```
<type>(mvp): <description>

Phase <N>: <context>

- Bullet points of changes
- Reference issue numbers if applicable
```

---

## Current Status: PHASE 0, DAY 1

**Next Action**: Audit existing FastAPI gateway structure

```bash
cd /home/user/Prep
source .venv/bin/activate

# Check what's already implemented
cat api/index.py
find api/ -name "*.py" -type f

# Check what's in prep/
ls -la prep/
cat prep/auth/core.py
cat prep/payments/stripe_client.py 2>/dev/null || echo "MISSING - needs creation"
```

**After audit, report back**:
1. What endpoints already exist in FastAPI?
2. What's missing vs. TS services?
3. Estimated hours to close the gap

---

**Document Owner**: Claude (AI Engineering Co-Founder)
**Last Updated**: 2025-11-30
**Status**: 🚨 ACTIVE - PHASE 0 IN PROGRESS
