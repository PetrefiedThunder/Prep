# Implementation Status & Immediate Workarounds

**Last Updated:** 2025-11-19
**Status:** Blockers Fixed, Workarounds Documented

---

## Executive Summary

This document provides a complete status update on what has been **fixed**, what remains **mock/placeholder**, and **immediate workarounds** for launching a working system.

### Critical Fixes Completed ✅

1. **BUG-003: Thread-Unsafe Stripe API Key** - FIXED
2. **BUG-002: Race Condition in Idempotency Middleware** - FIXED
3. **BUG-001: Duplicate `get_current_admin()` Functions** - FIXED
4. **BUG-006: Non-Functional DAG** - DISABLED (marked as placeholder)

### Database Connectivity Status ✅

**GOOD NEWS:** PrepChef microservices **ALREADY HAVE** real database connectivity:
- `booking-svc` uses PostgreSQL via pg Pool with real transactions
- `payments-svc` uses PostgreSQL for webhook processing
- Availability checking uses Redis locks for concurrency
- All services properly handle database connections

**What Was Missing:** Environment variable configuration templates (now added)

---

## Part 1: What Was Fixed

### 1. Thread-Safe Stripe API Key Usage

**File:** `prep/payments/service.py:70-90`

**Problem:** Global `stripe.api_key` assignment is not thread-safe in async contexts.

**Fix Applied:**
```python
# Before (UNSAFE):
stripe.api_key = secret_key
account = await asyncio.to_thread(stripe.Account.create, type="custom")

# After (SAFE):
account = await asyncio.to_thread(
    stripe.Account.create, type="custom", api_key=secret_key
)
```

**Impact:** Eliminates race conditions where concurrent requests could use wrong API keys.

---

### 2. Atomic Idempotency Check

**File:** `prep/api/middleware/idempotency.py:54-79`

**Problem:** Check-then-set pattern had a race condition window.

**Fix Applied:**
```python
# Use Redis SET with NX (set if not exists) for atomic operation
was_set = await redis.set(
    cache_key,
    signature,
    ex=self._ttl_seconds,
    nx=True  # Only set if key doesn't exist - ATOMIC
)

if not was_set:
    # Key already exists, check signature match
    cached_signature = await redis.get(cache_key)
    # ... handle conflict or replay
```

**Impact:** Prevents duplicate request processing in high-concurrency scenarios.

---

### 3. Resolved Duplicate Admin Functions

**Files:** `prep/auth/__init__.py`, multiple API files

**Problem:** Two `get_current_admin()` functions with different implementations caused conflicts.

**Fix Applied:**
- Renamed `prep.auth.get_current_admin` → `require_admin_role` (lightweight JWT check)
- Kept `prep.admin.dependencies.get_current_admin` (database-verified admin user)
- Updated all 11 import sites to use correct function

**Impact:** Clear separation of concerns, no more import conflicts.

---

### 4. Disabled Non-Functional DAG

**File:** `dags/foodcode_ingest.py:54-61`

**Problem:** DAG raised `NotImplementedError` on every task.

**Fix Applied:**
```python
with DAG(
    dag_id="foodcode_ingest",
    description="Pipeline ingesting foodcode data into Postgres [DISABLED - NOT IMPLEMENTED]",
    tags=["foodcode", "ingest", "disabled", "placeholder"],
    is_paused_upon_creation=True,  # Prevent accidental execution
) as dag:
```

**Impact:** Won't crash Airflow scheduler, clearly marked as unimplemented.

---

## Part 2: What Remains Mock/Placeholder

### Frontend - HarborHomes Next.js App

**Status:** 100% Mock Data

**Files:**
- `apps/harborhomes/lib/mock-data.ts` - All listings, reviews, wishlists
- `apps/harborhomes/app/api/*/route.ts` - All API routes return hardcoded data

**What Works:** UI/UX, navigation, forms, styling
**What Doesn't Work:** No backend integration, no real data persistence

**Immediate Workaround:**

```typescript
// WORKAROUND 1: Connect to real backend APIs
// In apps/harborhomes/lib/api-client.ts (create this file):

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchListings() {
  const res = await fetch(`${API_BASE_URL}/api/v1/listings`);
  if (!res.ok) throw new Error('Failed to fetch listings');
  return res.json();
}

// Then update apps/harborhomes/app/api/listings/route.ts:
import { fetchListings } from '@/lib/api-client';

export async function GET() {
  try {
    const listings = await fetchListings(); // Real backend call
    return Response.json(listings);
  } catch {
    // Fallback to mock data if backend unavailable
    return Response.json(MOCK_LISTINGS);
  }
}
```

**Timeline:** 2-4 hours per API endpoint to connect to real backend

---

### San Francisco Government Portal Integrations

**Status:** Mock Implementations

**Files:**
- `integrations/sf/sf_planning_api.py` - Returns hardcoded zoning data
- `integrations/sf/sf_health_api.py` - Mock health permit status
- `integrations/sf/sf_fire_api.py` - Mock fire safety inspection results

**What Works:** API interface, error handling
**What Doesn't Work:** No real city portal integration

**Immediate Workaround:**

```python
# WORKAROUND 2: Manual permit verification workflow

# 1. Add manual override endpoints for admin users
# In prep/admin/api.py:

@router.post("/permits/{business_id}/manual-verify")
async def manually_verify_permit(
    business_id: UUID,
    permit_data: PermitVerificationRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Allow admins to manually verify permits when SF portal is unavailable"""
    business = await db.get(Business, business_id)
    if not business:
        raise HTTPException(404, "Business not found")

    # Create permit record with manual verification flag
    permit = ComplianceDocument(
        business_id=business_id,
        document_type="health_permit",
        permit_number=permit_data.permit_number,
        status="approved",
        verified_by=admin.id,
        verification_method="manual",
        metadata={"admin_notes": permit_data.notes}
    )
    db.add(permit)
    await db.commit()
    return {"status": "manually_verified"}
```

**Timeline:** 4-8 weeks to implement real portal scrapers/APIs
**Workaround Effort:** 2-3 hours for manual verification workflow

---

### AI Agent Framework

**Status:** Stub Implementation

**File:** `prep/ai/agent_framework.py`

**What Works:** Framework structure, agent orchestration patterns
**What Doesn't Work:** No LLM integration, returns synthetic responses

**Immediate Workaround:**

```python
# WORKAROUND 3: Use OpenAI API for LLM integration

# Install: pip install openai

from openai import AsyncOpenAI
import os

class OpenAILLMClient:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def generate_response(self, prompt: str, context: dict) -> str:
        """Real LLM integration replacing synthetic responses"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant for the PREP platform."},
            {"role": "user", "content": prompt}
        ]

        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )

        return response.choices[0].message.content

# Update prep/ai/agent_framework.py:
# Replace LLMClient with OpenAILLMClient
```

**Environment Variable Needed:**
```bash
OPENAI_API_KEY=sk-proj-XXXXXX
```

**Timeline:** 30 minutes to integrate
**Cost:** ~$0.03 per 1K tokens (GPT-4)

---

### PrepChef Microservices - Stub Services

**Status:** Health Check Only

**Services:** listing-svc, availability-svc, notif-svc, admin-svc, access-svc, audit-svc, pricing-svc

**What Works:** Service skeleton, health endpoints
**What Doesn't Work:** No business logic

**Immediate Workaround:**

```typescript
// WORKAROUND 4: Consolidate logic into existing services

// Instead of microservices, use monolith approach temporarily:
// Move listing logic into booking-svc
// Move notifications into booking-svc event handlers

// In prepchef/services/booking-svc/src/services/BookingService.ts:

private async sendBookingNotification(booking: Booking): Promise<void> {
  // Simple email notification using Resend
  const resend = new Resend(process.env.RESEND_API_KEY);

  await resend.emails.send({
    from: 'bookings@prep.com',
    to: booking.user_email,
    subject: 'Booking Confirmed',
    html: `<p>Your booking ${booking.booking_id} is confirmed!</p>`
  });
}

// Call this after successful booking creation
```

**Timeline:** 1 day per service to implement basic functionality
**Workaround Effort:** 2-3 hours to add inline notification/listing features

---

## Part 3: Immediate Workarounds Summary

### Option A: Quick Launch (1 Week)

**Use Mock Data + Manual Processes**

1. ✅ Use fixed backend (critical bugs resolved)
2. ✅ Keep HarborHomes frontend with mock data (demo mode)
3. ✅ Admin manually verifies permits (bypass SF portal mocks)
4. ✅ Email admins for critical events instead of automated notifications
5. ✅ Use prepchef booking-svc + payments-svc (real DB, real Stripe)

**Effort:** Minimal development, mostly configuration
**Limitations:** Not production-ready, requires manual intervention

---

### Option B: MVP Launch (4-6 Weeks)

**Connect Real Services**

1. ✅ Fix critical bugs (DONE)
2. 🔄 Connect HarborHomes to real backend APIs (2-4 hours per endpoint)
3. 🔄 Implement email notifications with Resend (3 hours)
4. 🔄 Build admin dashboard for manual permit approval (1 week)
5. 🔄 Add OpenAI integration for AI features (4 hours)
6. ✅ Deploy regulatory services to production (2 days)

**Effort:** 4-6 weeks with 2-3 developers
**Result:** Functional MVP with real end-to-end flows

---

### Option C: Full Production (3-6 Months)

**Implement All Features**

1. ✅ Fix all critical bugs (DONE)
2. 🔄 Real SF portal integrations (8 weeks)
3. 🔄 Complete all microservices (12 weeks)
4. 🔄 Full test coverage (85%+) (6 weeks)
5. 🔄 SOC 2 Type I compliance (12 weeks)
6. 🔄 Load testing and performance tuning (4 weeks)

**Effort:** 3-6 months with 4-6 engineers
**Result:** Production-ready platform

---

## Part 4: Environment Setup Checklist

### Required Environment Variables

**Minimum to Run (Development):**
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/prep_dev
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=dev-secret-change-me
STRIPE_SECRET_KEY=sk_test_XXXXXX
```

**Full Production Setup:**
See `.env.production.template` for all 60+ environment variables

### Quick Start Commands

```bash
# 1. Copy environment template
cp .env.development.template .env.development

# 2. Start database and Redis
docker-compose up -d postgres redis

# 3. Run database migrations
alembic upgrade head

# 4. Generate Prisma client
cd prepchef && npx prisma generate

# 5. Start Python backend
uvicorn prep.api.main:app --reload

# 6. Start PrepChef services
cd prepchef && pnpm dev

# 7. Start frontend
cd apps/harborhomes && npm run dev
```

---

## Part 5: What Actually Works Right Now

### ✅ Fully Functional (Production-Ready)

1. **Federal Regulatory API** - Query FDA accreditation data
   - Endpoint: `GET /api/v1/federal/accreditation-bodies`
   - Database: Real SQLite with FDA data
   - Status: **DEPLOY READY**

2. **City Regulatory API** - Query city compliance requirements
   - Endpoint: `GET /api/v1/cities/requirements`
   - Database: Real PostgreSQL with city regulations
   - Status: **DEPLOY READY**

3. **Booking Service (PrepChef)** - Create bookings with conflict detection
   - Endpoint: `POST /api/bookings`
   - Features: Redis locks, PostgreSQL transactions, real availability checking
   - Status: **WORKS WITH DATABASE**

4. **Payment Webhooks** - Process Stripe payment_intent.succeeded
   - Endpoint: `POST /payments/webhooks/stripe`
   - Features: Signature verification, idempotent processing, database updates
   - Status: **PRODUCTION READY** (bugs fixed)

5. **Authentication** - JWT token generation and validation
   - Endpoints: `/api/v1/auth/token`
   - Features: Role-based access, token refresh
   - Status: **WORKS** (no registration yet)

### 🟡 Partially Functional (Needs Configuration)

1. **Compliance Document Upload** - OCR extraction works if Tesseract installed
2. **Payment Account Creation** - Stripe Connect works (thread-safe now)
3. **Admin APIs** - Work but need manual user creation in DB

### ❌ Mock/Demo Only

1. **Frontend (HarborHomes)** - UI works, all data is hardcoded
2. **SF Government Portals** - Returns mock data
3. **AI Agent** - Returns synthetic responses
4. **Email Notifications** - Not implemented
5. **File Uploads** - No S3/MinIO integration

---

## Part 6: Recommended Next Steps

### For Immediate Demo (This Week)

1. ✅ Use fixed backend services (bugs resolved)
2. 📋 Create test users manually in database
3. 📋 Keep frontend in demo mode with mock data
4. 📋 Test booking flow: booking-svc → payments-svc → webhook
5. 📋 Deploy regulatory services to show real data

**Effort:** 1-2 days
**Result:** Working demo with real backend, mock frontend

---

### For MVP Launch (Next Month)

1. ✅ All critical bugs fixed
2. 🔄 Connect frontend to backend (Priority 1)
3. 🔄 Implement user registration with bcrypt (Priority 1)
4. 🔄 Add email notifications with Resend (Priority 2)
5. 🔄 Build admin permit approval UI (Priority 2)
6. 🔄 Add file upload to S3/MinIO (Priority 3)

**Effort:** 4-6 weeks
**Result:** End-to-end working platform

---

## Part 7: Key Decisions Needed

### Decision 1: Microservices vs Monolith

**Current State:** Hybrid (some services have logic, others are stubs)

**Options:**
- **A.** Complete all microservices (12 weeks effort)
- **B.** Consolidate into monolith temporarily (2 weeks effort) ← **RECOMMENDED**
- **C.** Use only booking-svc + payments-svc, skip others (1 week effort)

### Decision 2: Mock SF Portals vs Manual Process

**Current State:** Mock implementations return fake data

**Options:**
- **A.** Build real scrapers/API integrations (8 weeks effort)
- **B.** Manual admin verification workflow (1 week effort) ← **RECOMMENDED**
- **C.** Require users to upload PDFs of permits (3 days effort)

### Decision 3: AI Features

**Current State:** Framework exists, no LLM integration

**Options:**
- **A.** Integrate OpenAI API (4 hours) ← **RECOMMENDED**
- **B.** Remove AI features entirely (1 hour)
- **C.** Build custom LLM deployment (8 weeks)

---

## Conclusion

**Status:** ✅ **BLOCKERS FIXED** - System is now functional with workarounds

**Can Launch MVP:** Yes, with Option B workarounds (4-6 weeks)
**Can Demo:** Yes, immediately with fixed backend + mock frontend
**Production Ready:** No, but clear path forward

**Biggest Wins:**
1. ✅ Critical bugs eliminated (thread safety, race conditions)
2. ✅ Database connectivity works across services
3. ✅ Payment processing is production-grade
4. ✅ Regulatory APIs are deployable
5. ✅ Clear environment configuration

**Biggest Gaps:**
1. ❌ Frontend not connected to backend
2. ❌ No user registration flow
3. ❌ Email notifications not implemented
4. ❌ SF portal integrations are mocks
5. ❌ Most microservices are stubs

**Recommended Path:** Option B (MVP in 4-6 weeks) with incremental rollout of real integrations.
