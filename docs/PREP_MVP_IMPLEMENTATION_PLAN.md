# Prep MVP v1.0 - Comprehensive Implementation Plan

**Date:** October 22, 2025
**Status:** 15-20% Complete (Planning & Scaffolding Phase)
**Target Launch:** 10 weeks from kickoff

---

## Executive Summary

**PrepChef** is a commercial kitchen rental marketplace connecting certified kitchens with food entrepreneurs. The platform currently has:
- ✅ Production-ready PostgreSQL schema (448 lines, 13 tables)
- ✅ Comprehensive planning documentation (10-week engineering plan)
- ✅ Fastify microservices scaffolding (11 services)
- ✅ Basic React frontend structure
- ❌ No database connection or ORM
- ❌ No payment integration
- ❌ No third-party service integrations
- ❌ Minimal business logic implementation

**Critical Decision Point**: The current architecture uses 11 Fastify microservices, but the engineering plan recommends starting with a monolithic Node.js app for MVP simplicity. **Recommendation: Consolidate to monolith for MVP**, then extract services post-launch.

---

## Current State Analysis

### What Exists (Completed)

#### 1. Database Schema (`prepchef/db/schema.sql`) - 100% Complete
Production-ready schema with:
- **Users & Auth**: `users`, `businesses` tables with role-based access
- **Listings**: `venues`, `kitchen_listings`, `availability_windows`, `compliance_documents`
- **Bookings**: `bookings`, `access_grants` (smart lock integration ready)
- **Social**: `reviews`, `messages`, `notifications`
- **Audit**: `audit_logs` for compliance tracking
- **Advanced Features**:
  - PostGIS for geospatial queries
  - Row-Level Security (RLS) policies
  - Full-text search indexes
  - Materialized view for listing statistics
  - Booking conflict prevention via exclusion constraints

**Gap**: Schema is not applied to any database. No migrations framework configured.

#### 2. Service Architecture - 20% Complete

**Implemented Services** (Fastify-based):
```
prepchef/
├── services/
│   ├── auth-svc       → Basic JWT login/refresh (hardcoded admin/secret)
│   ├── booking-svc    → Orchestration pattern (calls fake URLs)
│   ├── pricing-svc    → Working calculation logic ($50/hr + fees)
│   ├── compliance-svc → 737 lines of validation logic
│   ├── availability-svc → Stub only
│   ├── listing-svc    → Stub only
│   ├── payments-svc   → Stub only
│   ├── notif-svc      → Stub only
│   ├── admin-svc      → Stub only
│   ├── access-svc     → Stub only
│   └── audit-svc      → Stub only
```

**Key Issues**:
- Services use internal service mesh URLs (`http://compliance/check`) that don't resolve
- No database client instantiated anywhere
- No environment-based configuration
- Mock implementations everywhere

#### 3. Frontend (`apps/web`) - 10% Complete

**Tech Stack**: React 18.2 + Vite 5.0 + TailwindCSS 3.4 + React Router 6.22

**Implemented Pages**:
- `LandingPage.tsx` - Basic hero section
- `KitchenBrowser.tsx` - Empty list with placeholder fetch
- `BookingCheckout.tsx` - Form skeleton
- `Dashboard.tsx` - Empty dashboard

**Missing**:
- ❌ State management (Zustand specified but not installed)
- ❌ Data fetching (no SWR/TanStack Query)
- ❌ Authentication UI
- ❌ Kitchen detail page
- ❌ Host/Admin dashboards
- ❌ Form validation (no Zod schemas)
- ❌ PWA configuration (no service workers)

#### 4. Documentation - 95% Complete
- ✅ Technical Outline (TECHNICAL_OUTLINE.md)
- ✅ 10-Week Engineering Plan (prepchef_mvp_engineering_plan.md)
- ✅ Gap Analysis (prep_mvp_gap_analysis.md)
- ✅ OpenAPI contracts defined (contracts/openapi.yaml)

---

## Critical Gaps vs. Technical Outline

### Infrastructure Gaps

| Component | Required | Current State | Priority |
|-----------|----------|---------------|----------|
| **Database** | PostgreSQL 15 (Supabase) | Schema only, not deployed | 🔴 Critical |
| **ORM** | Prisma or Drizzle | Not installed | 🔴 Critical |
| **Redis** | Session store + cache | Not configured | 🟡 Medium |
| **File Storage** | Supabase Storage / S3 | Not configured | 🟡 Medium |
| **Environment Config** | .env with Doppler | Partial | 🔴 Critical |

### Backend Service Gaps

| Service | Implementation % | Critical Missing Features |
|---------|------------------|---------------------------|
| **auth-svc** | 30% | User registration, password hashing (bcrypt), email verification, database lookup |
| **listing-svc** | 5% | Kitchen CRUD, photo upload, geospatial search, availability management |
| **booking-svc** | 15% | Conflict detection, status workflow, payment capture, notifications |
| **payments-svc** | 0% | Stripe SDK, Connect onboarding, payment intents, webhooks |
| **notif-svc** | 0% | Resend/SendGrid integration, SMS (Twilio), push notifications |
| **admin-svc** | 0% | Certification approval queue, user moderation, analytics |
| **compliance-svc** | 60% | Document upload, expiry tracking, admin review workflow |
| **availability-svc** | 0% | Calendar management, Redis cache, conflict detection |
| **pricing-svc** | 80% | Tax calculation, dynamic pricing, cancellation refunds |

### Frontend Gaps

| Component | Status | Missing |
|-----------|--------|---------|
| **Authentication** | ❌ Not started | Login/signup forms, JWT storage, protected routes |
| **Kitchen Discovery** | 🟡 10% | Search filters, map view, calendar availability |
| **Booking Flow** | 🟡 20% | Date picker, pricing preview, payment form (Stripe Elements) |
| **User Dashboard** | ❌ Not started | Booking history, messages, payment methods |
| **Host Dashboard** | ❌ Not started | Listing editor, calendar, earnings, analytics |
| **Admin Panel** | ❌ Not started | Certification queue, user management, platform metrics |
| **State Management** | ❌ Not installed | Zustand for auth + user state |
| **PWA** | ❌ Not configured | Service workers, manifest.json, offline support |

### Third-Party Integrations

| Integration | Purpose | Status |
|-------------|---------|--------|
| **Stripe** | Payments + Connect | ❌ SDK not installed |
| **Resend/SendGrid** | Email notifications | ❌ Not configured |
| **Twilio** | SMS notifications | ❌ Not configured |
| **Supabase** | Database + storage + auth | ❌ Project not created |
| **Google Maps** | Geolocation + address autocomplete | ❌ Not configured |
| **PostHog** | Analytics | ❌ Not configured |
| **Sentry** | Error tracking | ❌ Not configured |

---

## Recommended Implementation Roadmap

### Architecture Decision: Monolith vs. Microservices

**Current**: 11 separate Fastify services
**Recommendation**: **Consolidate to single Express/Fastify monolith for MVP**

**Rationale**:
1. Faster development velocity (no inter-service communication debugging)
2. Simplified deployment (single Docker container)
3. Easier local development (one process to run)
4. Lower infrastructure costs
5. Engineering plan explicitly recommends this approach

**Migration Path**:
```
Current: 11 services on random ports (3000-4000)
  ↓
MVP: Single app on port 3000 with route prefixes:
  /api/auth/*
  /api/kitchens/*
  /api/bookings/*
  /api/admin/*
  ↓
Post-MVP: Extract high-traffic services (payments, booking) as needed
```

---

## 10-Week Implementation Plan (Aligned with Engineering Plan)

### Phase 1: Foundation & Core Infrastructure (Weeks 1-2)

**Goal**: Get database connected, authentication working, and CI/CD operational.

#### Week 1: Infrastructure Setup
- [ ] Create Supabase project and apply `prepchef/db/schema.sql`
- [ ] Install Prisma ORM and generate client from existing schema
- [ ] Set up Doppler for secrets management (or Vercel/Fly.io secrets)
- [ ] Configure GitHub Actions CI pipeline:
  - ESLint + Prettier
  - TypeScript type checking
  - Unit tests with Jest
- [ ] Create Docker Compose for local development:
  - PostgreSQL 15
  - Redis 7
  - MinIO (S3 mock)
  - MailHog (email testing)
- [ ] Deploy "hello world" to staging (Fly.io + Vercel)

**Exit Criteria**:
- ✅ `npm run dev` starts entire stack locally
- ✅ Prisma client connects to PostgreSQL
- ✅ CI passes on every PR
- ✅ Staging environment accessible

#### Week 2: Authentication & User Management
- [ ] Consolidate auth-svc into monolith `/api/auth/*`
- [ ] Implement user registration with bcrypt password hashing
- [ ] Add email verification flow (Resend API)
- [ ] Create JWT middleware with role-based access control (RBAC)
- [ ] Build frontend auth pages:
  - Login form with validation
  - Registration form
  - Email verification screen
  - Password reset flow
- [ ] Install Zustand and create auth store
- [ ] Protected routes in React Router
- [ ] Write integration tests for auth endpoints

**Exit Criteria**:
- ✅ Users can sign up, verify email, and log in
- ✅ JWT tokens stored in httpOnly cookies
- ✅ RBAC middleware blocks unauthorized access
- ✅ 80%+ test coverage for auth module

---

### Phase 2: Host & Kitchen Management (Weeks 3-5)

**Goal**: Hosts can create listings with photos and compliance documents.

#### Week 3: Kitchen Listings CRUD
- [ ] Implement listing-svc as `/api/kitchens/*`:
  - `POST /api/kitchens` - Create listing
  - `GET /api/kitchens` - List with filters (location, price, equipment)
  - `GET /api/kitchens/:id` - Single listing detail
  - `PATCH /api/kitchens/:id` - Update listing
  - `DELETE /api/kitchens/:id` - Soft delete
- [ ] Set up Supabase Storage for photos:
  - Signed URL upload flow
  - Client-side image compression (browser-image-compression)
  - Maximum 10 photos per listing
- [ ] Build frontend kitchen editor:
  - Multi-step form wizard (Basic Info → Location → Pricing → Equipment → Photos)
  - Drag-and-drop photo upload
  - Address autocomplete (Google Places API)
  - Equipment checklist
- [ ] Implement PostGIS geospatial search:
  - Radius-based filtering
  - Bounding box queries
- [ ] Write E2E test: Host creates listing with photos

**Exit Criteria**:
- ✅ Hosts can create/edit/delete listings via UI
- ✅ Photos upload to Supabase Storage
- ✅ Search filters work (location, price, equipment)
- ✅ Kitchen detail page renders with all data

#### Week 4: Compliance & Certification
- [ ] Build compliance document upload flow:
  - Health certificate
  - Business license
  - Insurance proof
- [ ] Create admin review queue:
  - Table view of pending documents
  - Approve/reject actions
  - Notification to host on status change
- [ ] Implement document expiry tracking:
  - Cron job to check expiring certificates (30 days warning)
  - Email reminders to hosts
  - Auto-flag listings with expired certs
- [ ] Frontend compliance UI:
  - Host dashboard compliance section
  - Upload widget with file type validation
  - Status badges (Pending, Approved, Rejected, Expired)

**Exit Criteria**:
- ✅ Hosts upload compliance docs
- ✅ Admins approve/reject via admin panel
- ✅ Expiring certificates trigger email alerts
- ✅ Listings cannot be published without approved certs

#### Week 5: Availability Management
- [ ] Implement availability-svc:
  - `POST /api/kitchens/:id/availability` - Set recurring hours
  - `GET /api/kitchens/:id/availability` - Get available slots
  - `DELETE /api/availability/:id` - Remove availability window
- [ ] Build calendar UI component:
  - Weekly recurring hours picker
  - One-off date blocking
  - Preview of available slots
- [ ] Redis caching layer:
  - Cache availability windows by kitchen_id
  - Invalidate on booking creation/cancellation
  - TTL aligned with database `updated_at` timestamps
- [ ] Conflict detection logic:
  - Check `availability_windows` table
  - Enforce buffer time between bookings
  - Block overlapping reservations

**Exit Criteria**:
- ✅ Hosts set weekly availability schedules
- ✅ Renter sees accurate available time slots
- ✅ Redis cache reduces database load
- ✅ Conflict detection prevents double-bookings

---

### Phase 3: Renter Discovery & Booking (Weeks 6-8)

**Goal**: Renters can search kitchens, check availability, and complete bookings with payment.

#### Week 6: Search & Discovery
- [ ] Build kitchen browser UI:
  - Search bar with location autocomplete
  - Filter panel (price, equipment, certifications, availability)
  - Grid/list view toggle
  - Map view (Google Maps integration)
- [ ] Implement search API:
  - Full-text search on title + description
  - PostGIS radius queries
  - Filter by availability window
  - Sort by price, rating, distance
- [ ] Kitchen detail page:
  - Photo gallery
  - Amenities list
  - Reviews section
  - Availability calendar
  - "Book Now" CTA

**Exit Criteria**:
- ✅ Renters search kitchens by location + filters
- ✅ Map shows kitchen locations with pins
- ✅ Detail page displays complete listing info
- ✅ Search returns results in <500ms (p95)

#### Week 7: Booking Flow & Payments
- [ ] Install Stripe SDK and configure webhooks:
  - Payment Intents API
  - Stripe Elements for frontend
  - Webhook endpoints for payment events
- [ ] Implement booking-svc:
  - `POST /api/bookings` - Create booking with payment
  - `GET /api/bookings/:id` - Get booking details
  - `PATCH /api/bookings/:id/cancel` - Cancel with refund logic
  - `POST /api/bookings/:id/complete` - Mark completed
- [ ] Build checkout flow:
  - Date/time picker
  - Real-time pricing calculator
  - Stripe payment form (Stripe Elements)
  - Booking confirmation screen
- [ ] Booking status workflow:
  - `requested` → `payment_authorized` → `confirmed` → `active` → `completed`
  - Automatic state transitions based on time
  - Cancellation policy enforcement
- [ ] Notification service:
  - Email: Booking confirmation, reminder (24h before), completion
  - SMS: Booking reminder (optional)
  - In-app: Real-time booking status updates

**Exit Criteria**:
- ✅ Renters complete end-to-end booking + payment
- ✅ Stripe payment intents captured successfully
- ✅ Booking confirmation emails sent
- ✅ Cancellation refunds processed correctly

#### Week 8: Messaging & User Dashboard
- [ ] Implement messaging system:
  - `POST /api/messages` - Send message
  - `GET /api/messages/:conversationId` - Get thread
  - Real-time updates via WebSockets (Socket.IO)
- [ ] Build user dashboard:
  - Upcoming bookings
  - Past bookings
  - Messages inbox
  - Payment methods
- [ ] Build host dashboard:
  - Calendar view of bookings
  - Earnings summary
  - Active listings
  - Messages inbox

**Exit Criteria**:
- ✅ Renters and hosts exchange messages
- ✅ Dashboards display relevant booking data
- ✅ Real-time message notifications work

---

### Phase 4: Payments, Polish & Launch (Weeks 9-10)

**Goal**: Stripe Connect payouts, reviews, production readiness.

#### Week 9: Stripe Connect & Payouts
- [ ] Implement Stripe Connect Custom accounts:
  - Host onboarding flow
  - KYC verification webhooks
  - Payout account status tracking
- [ ] Build payout automation:
  - Automatic transfer on booking completion
  - Retry logic for failed payouts (BullMQ)
  - Finance ledger table for audit trail
- [ ] Host earnings dashboard:
  - Total earnings
  - Pending payouts
  - Payout history
  - Connect account status

**Exit Criteria**:
- ✅ Hosts complete Stripe Connect onboarding
- ✅ Payouts trigger automatically after bookings
- ✅ Failed payouts retry up to 3 times
- ✅ Financial ledger tracks all transactions

#### Week 10: Reviews, Hardening & Launch
- [ ] Implement review system:
  - Two-sided reviews (renter ↔ host)
  - Unlock 24 hours after booking completion
  - 5-star rating with categories (cleanliness, equipment, location, value)
  - Abuse reporting
- [ ] Polish & bug fixes:
  - Accessibility audit (WCAG 2.1 AA)
  - Performance optimization (Lighthouse score ≥85)
  - Mobile responsive testing
  - Cross-browser testing
- [ ] Production hardening:
  - Set up Sentry for error tracking
  - Configure Grafana dashboards
  - PagerDuty alerts for critical errors
  - Rate limiting (Redis + express-rate-limit)
  - OWASP security headers (Helmet)
- [ ] Launch checklist:
  - [ ] Seed 10 launch kitchens
  - [ ] Create test renter accounts
  - [ ] Dry run: full booking flow end-to-end
  - [ ] Legal: Terms of Service + Privacy Policy live
  - [ ] Support: Canned responses for top 10 issues
  - [ ] Monitoring: All alerts configured

**Exit Criteria**:
- ✅ Review system fully operational
- ✅ Lighthouse PWA score ≥85
- ✅ All production monitoring active
- ✅ Launch checklist 100% complete

---

## Technical Stack (Final)

### Frontend
- **Framework**: React 18.2 + Vite 5.0
- **Styling**: TailwindCSS 3.4
- **State**: Zustand (auth, user data)
- **Forms**: React Hook Form + Zod validation
- **Data Fetching**: TanStack Query (React Query)
- **Maps**: Google Maps JavaScript API
- **Payments**: Stripe Elements
- **Real-time**: Socket.IO client
- **PWA**: Vite PWA plugin
- **Deployment**: Vercel

### Backend
- **Runtime**: Node.js 20 LTS
- **Framework**: Fastify 4.28 (consolidate microservices)
- **ORM**: Prisma 5.x
- **Database**: PostgreSQL 15 (Supabase)
- **Cache**: Redis 7 (Upstash or Supabase Redis)
- **Auth**: JWT (@fastify/jwt)
- **Validation**: Zod
- **Jobs**: BullMQ (payout retries, email queue)
- **File Storage**: Supabase Storage
- **Real-time**: Socket.IO
- **Deployment**: Fly.io (Docker)

### Third-Party Services
- **Payments**: Stripe (Payment Intents + Connect)
- **Email**: Resend (transactional emails)
- **SMS**: Twilio (optional for MVP)
- **Maps**: Google Maps Platform (Places API + Maps JavaScript API)
- **Analytics**: PostHog (self-hosted or cloud)
- **Monitoring**: Sentry (errors) + Grafana Cloud (metrics)
- **Secrets**: Doppler or Fly.io secrets

---

## Critical Dependencies & Packages to Install

### Backend (Monolith)
```json
{
  "dependencies": {
    "fastify": "^4.28.0",
    "@fastify/cors": "^9.0.1",
    "@fastify/jwt": "^8.0.0",
    "@fastify/cookie": "^9.0.0",
    "@fastify/rate-limit": "^9.0.0",
    "@fastify/helmet": "^11.0.0",
    "@prisma/client": "^5.20.0",
    "prisma": "^5.20.0",
    "zod": "^3.22.0",
    "bcrypt": "^5.1.1",
    "stripe": "^14.0.0",
    "resend": "^2.0.0",
    "twilio": "^4.19.0",
    "ioredis": "^5.3.2",
    "bullmq": "^5.0.0",
    "socket.io": "^4.6.0",
    "undici": "^6.0.0"
  },
  "devDependencies": {
    "@types/bcrypt": "^5.0.0",
    "vitest": "^1.0.0",
    "supertest": "^6.3.3"
  }
}
```

### Frontend
```json
{
  "dependencies": {
    "zustand": "^4.4.7",
    "@tanstack/react-query": "^5.0.0",
    "react-hook-form": "^7.48.2",
    "@stripe/stripe-js": "^2.2.0",
    "@stripe/react-stripe-js": "^2.4.0",
    "socket.io-client": "^4.6.0",
    "@googlemaps/js-api-loader": "^1.16.2",
    "date-fns": "^2.30.0",
    "react-day-picker": "^8.9.1"
  },
  "devDependencies": {
    "vite-plugin-pwa": "^0.17.0",
    "@playwright/test": "^1.40.0"
  }
}
```

---

## Testing Strategy

### Unit Tests (≥80% coverage)
- **Backend**: Jest + Supertest
  - Auth: Registration, login, JWT validation
  - Booking: Conflict detection, pricing calculation
  - Payments: Stripe webhook handling
- **Frontend**: Vitest + React Testing Library
  - Forms: Validation logic
  - Components: Kitchen card, booking calendar
  - Stores: Zustand auth store

### Integration Tests
- Database test containers (Testcontainers)
- Mock Stripe webhooks
- Happy path: Host creates listing → Renter books → Payment captured

### E2E Tests (Playwright)
- Critical user journeys:
  1. Host onboarding → Create listing → Upload photos
  2. Renter search → Book kitchen → Complete payment
  3. Admin approve compliance documents

### Performance Tests
- k6 load tests for booking API (p95 <500ms)
- Lighthouse CI for PWA score (≥85)

---

## DevOps & Infrastructure

### Local Development
```bash
# Start all services
docker-compose up -d  # PostgreSQL, Redis, MinIO, MailHog

# Run database migrations
cd prepchef
npx prisma migrate dev

# Start backend
npm run dev -w services/api-svc  # Port 3000

# Start frontend
cd apps/web
npm run dev  # Port 5173
```

### CI/CD Pipeline (GitHub Actions)
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    - Lint (ESLint + Prettier)
    - Type check (TypeScript)
    - Unit tests (Jest)
    - Build (npm run build)

  deploy-staging:
    if: branch == 'develop'
    - Deploy backend to Fly.io staging
    - Deploy frontend to Vercel preview

  deploy-prod:
    if: branch == 'main'
    - Run E2E tests (Playwright)
    - Manual approval gate
    - Deploy backend to Fly.io production
    - Deploy frontend to Vercel production
```

### Monitoring & Alerts
- **Errors**: Sentry (PagerDuty for Sev1)
- **Performance**: Grafana dashboards
  - API latency (p50, p95, p99)
  - Booking conversion rate
  - Stripe webhook failures
- **Uptime**: Upptime (status page)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| **Stripe Connect onboarding delays** | Pre-launch checklist, proactive support, manual payout fallback |
| **Double-booking due to race conditions** | PostgreSQL exclusion constraints + Redis locks + automated reconciliation |
| **Compliance document fraud** | Admin manual review + third-party validation (Phase 2) |
| **Performance under load** | k6 load tests + Fly.io auto-scaling + CDN for static assets |
| **Data privacy incidents** | RLS policies + encrypted backups + incident response playbook |

---

## Success Metrics (MVP Launch)

### Technical Metrics
- [ ] 10 vetted kitchens live on platform
- [ ] ≥5 test bookings completed successfully
- [ ] API p95 latency <500ms
- [ ] PWA Lighthouse score ≥85
- [ ] Test coverage ≥80% for critical paths
- [ ] Zero Sev1 incidents in first 48 hours

### Business Metrics (Post-Launch)
- Month 1: 10 kitchens, 20 bookings
- Month 3: 50 kitchens, 100 bookings
- Month 6: 3-city expansion

---

## Immediate Next Steps (Week 0)

### Priority 1: Infrastructure
1. [ ] Create Supabase project (`prepchef-mvp`)
2. [ ] Apply `prepchef/db/schema.sql` via Supabase dashboard
3. [ ] Install Prisma: `cd prepchef && npm install prisma @prisma/client`
4. [ ] Generate Prisma client from existing schema: `npx prisma db pull && npx prisma generate`
5. [ ] Test database connection: Write simple query in `auth-svc`

### Priority 2: Consolidate Services
1. [ ] Create new monolith: `prepchef/services/api-svc`
2. [ ] Copy auth-svc routes into `/api/auth/*`
3. [ ] Set up Prisma client singleton
4. [ ] Replace hardcoded credentials with database lookup
5. [ ] Delete or archive old microservices

### Priority 3: Frontend Foundations
1. [ ] Install Zustand: `cd apps/web && npm install zustand`
2. [ ] Install TanStack Query: `npm install @tanstack/react-query`
3. [ ] Create auth store (`src/stores/authStore.ts`)
4. [ ] Build login/signup forms
5. [ ] Set up protected routes

### Priority 4: CI/CD
1. [ ] Create `.github/workflows/ci.yml`
2. [ ] Configure Fly.io deployment
3. [ ] Configure Vercel deployment
4. [ ] Set up Doppler for secrets management

---

## Open Questions & Decisions Needed

1. **Architecture**: Confirm monolith vs. microservices decision
2. **Hosting**: Supabase vs. self-hosted PostgreSQL?
3. **Auth**: Continue with custom JWT or use Supabase Auth?
4. **Email**: Resend vs. SendGrid?
5. **Maps**: Confirm Google Maps budget (or use Mapbox?)
6. **Redis**: Upstash (serverless) vs. Redis Labs vs. Supabase Redis?

---

## Conclusion

The Prep platform has **strong foundations** (excellent planning, production-ready schema) but requires **focused execution** on:
1. Database connectivity (Prisma + Supabase)
2. Real authentication (bcrypt + email verification)
3. Core CRUD operations (kitchens, bookings)
4. Payment integration (Stripe)
5. Frontend-backend integration

By consolidating to a **monolith architecture** and following the **10-week phased plan**, the MVP can launch on schedule with:
- 10 certified kitchens
- End-to-end booking + payment flow
- Host and renter dashboards
- Admin certification approval
- Production monitoring

**Next Step**: Review this plan with stakeholders and proceed with Week 0 infrastructure setup.
