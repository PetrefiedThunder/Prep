# Prep MVP Critical Path – "MVP OR BUST"

Goal:
By **Dec 7, 2025 @ 11:59 PM PT**, a non-founder can complete a **$100+ booking** in Stripe test mode, end-to-end, with **no manual steps** using only:

- FastAPI API Gateway
- Next.js (HarborHomes)
- Postgres + Redis

This document defines the **minimum set of work** required to reach that goal.
If a task is not on this path, it is **POST-MVP** by default.

---

## Phase 0 – Baseline: Repo Up, Services Healthy

**Objective:** Any dev can run the stack and hit basic health endpoints.

- [ ] `make bootstrap` succeeds locally on a clean machine
- [ ] `make health` passes for:
  - API Gateway (FastAPI)
  - HarborHomes (Next.js)
  - Postgres + Redis
- [ ] Document any required env vars in `.env.example` and `DEVELOPER_ONBOARDING.md`
- [ ] CI: `make lint`, `make typecheck`, and `make test` all green on main

**Exit criteria:**
> A new developer can clone, bootstrap, and see a "Hello, world" from the frontend and API without touching any code.

---

## Phase 1 – Backend Happy Path

**Objective:** Implement a **real** signup → search → booking → payment flow, API-first.

### 1. Auth & Users

- [ ] Create user signup & login endpoints in FastAPI
- [ ] Persist users in Postgres (no mocks)
- [ ] JWT auth with:
  - [ ] Access tokens (≈15 min)
  - [ ] Refresh tokens (≈7 days)
- [ ] Basic RBAC: `customer` vs `admin`

**Exit:**
> You can `curl` or use an HTTP client to create a user, log in, and call a protected endpoint.

### 2. Kitchens & Listings

- [ ] Define `kitchens` schema in Postgres (or confirm existing)
- [ ] Seed at least **5 real SF kitchens** with:
  - [ ] Name, address, geo-coordinates
  - [ ] Capacity / hourly rate
  - [ ] Basic availability windows
- [ ] Implement API endpoints:
  - [ ] `GET /api/kitchens/search` with basic filters (location, date/time window)
  - [ ] `GET /api/kitchens/{id}`

**Exit:**
> You can hit `/api/kitchens/search` and get back seeded SF kitchens from Postgres.

### 3. Booking Engine (Minimal)

- [ ] Define `bookings` table with:
  - [ ] `user_id`, `kitchen_id`, `start_time`, `end_time`, `status`, `total_amount`
- [ ] Implement conflict detection:
  - [ ] Query existing bookings for same kitchen
  - [ ] Reject overlapping time ranges
- [ ] Implement endpoints:
  - [ ] `POST /api/bookings` – create tentative booking (status: `pending_payment`)
  - [ ] `GET /api/bookings/{id}` – fetch booking detail
- [ ] Use Redis locks or a simple transactional approach to avoid race conditions on double booking

**Exit:**
> You can POST a booking for a valid window and see it persisted, and overlapping windows are rejected.

### 4. Stripe Integration (Backend)

- [ ] Implement Stripe Checkout session creation:
  - [ ] `POST /api/payments/checkout` → returns `checkout_url` for Stripe
  - [ ] Amount derived from booking's `total_amount`
- [ ] Implement Stripe webhook handler:
  - [ ] On successful payment, set booking status → `paid`
  - [ ] On failure/expiration, set status → `payment_failed` or `expired`
- [ ] Persist Stripe IDs (session, payment intent) in DB

**Exit:**
> From the backend alone, you can create a booking, generate a Stripe Checkout URL, pay in test mode, and see the booking updated to `paid` via the webhook.

---

## Phase 2 – Frontend Wiring (HarborHomes)

**Objective:** Replace mocks with **real API calls** for the MVP happy path.

### 1. Auth UI

- [ ] Wire signup/login pages to real FastAPI endpoints
- [ ] Store JWT securely (HTTP-only cookie or safe storage strategy)
- [ ] Show logged-in state in the UI (e.g., user menu)

### 2. Kitchen Search & Detail

- [ ] Replace any `mockKitchens` / `mockSearchResults` with calls to `/api/kitchens/search`
- [ ] Use real kitchen detail endpoint for kitchen view page
- [ ] Basic error handling & loading states

### 3. Booking Flow UI

- [ ] On the kitchen detail page:
  - [ ] Let user pick date/time + duration
  - [ ] Call `POST /api/bookings` to create `pending_payment` booking
- [ ] On booking confirmation step:
  - [ ] Call `POST /api/payments/checkout`
  - [ ] Redirect user to Stripe Checkout URL
- [ ] After payment:
  - [ ] Implement a `/booking/complete` page that:
    - [ ] Uses booking ID or a Stripe reference to fetch final booking
    - [ ] Shows status (`paid`) and key details

**Exit:**
> From the browser, you can log in, search, book, pay (Stripe test), and see a confirmation page—all backed by real APIs & DB.

---

## Phase 3 – E2E Tests & Coverage

**Objective:** Lock the happy path into automated tests and meet coverage targets.

### 1. Playwright E2E

- [ ] Write a Playwright test that:
  - [ ] Creates a user (or uses a seeded test user)
  - [ ] Logs in
  - [ ] Searches for a kitchen
  - [ ] Creates a booking
  - [ ] Goes through Stripe test checkout (use Stripe test card)
  - [ ] Verifies the final receipt/confirmation page

- [ ] Integrate Playwright E2E into CI (`make test-e2e` or npm script)

### 2. Backend Tests

- [ ] Unit tests for:
  - [ ] Booking conflict detection
  - [ ] Stripe webhook handler
  - [ ] Auth token creation/validation
- [ ] Integration tests using a real test DB

### 3. Coverage

- [ ] Raise coverage to **≥ 55%** overall
- [ ] Ensure auth + booking + payments paths are **~100%** covered

**Exit:**
> CI runs Playwright + pytest on every push to main, green >95% of the time.

---

## Phase 4 – Hardening & Buffer

**Objective:** Use remaining time to de-risk deployment and UX for the MVP demo.

- [ ] 1–2 rounds of "stranger testing" (non-founder runs the flow)
- [ ] Fix top UX papercuts (form validation, error messages)
- [ ] Basic logging & metrics for:
  - [ ] Booking creation
  - [ ] Payment success/failure
- [ ] Update:
  - [ ] `README.md` – add "How to run the MVP demo" section
  - [ ] `DEVELOPER_ONBOARDING.md` – reflect the happy path and commands
  - [ ] `PREP_MVP_IMPLEMENTATION_PLAN.md` – mark completed items

**Final Exit Criteria:**
> At least one non-founder can follow README instructions to run the stack locally and complete a $100+ booking in Stripe test mode, with zero manual DB tweaks, and all tests passing in CI.
