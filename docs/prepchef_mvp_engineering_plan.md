# PrepChef MVP v1.0 Engineering Plan

**Revision Date:** October 20, 2025

**Goal:** Launch a minimum viable marketplace that lets certified commercial kitchens rent unused capacity to verified food entrepreneurs while maintaining regulatory compliance and reliable payment flows.

---

## 1. Phased Development Timeline & Milestones

The MVP delivery is organized into four execution phases. Each phase concludes with explicit exit criteria to prevent downstream rework.

| Phase | Duration | Engineering Focus | Exit Criteria |
| :--- | :--- | :--- | :--- |
| **1. Foundation & Core Infrastructure** | Weeks 1–2 | Project scaffolding, auth baseline, observability, developer experience. | ✅ Frontend/backends bootstrapped and deployed to staging.<br>✅ PostgreSQL schema migrated with baseline seed data.<br>✅ Auth service issues JWT access+refresh tokens and rotates secrets via Fly.io secrets manager.<br>✅ CI runs lint, unit tests, and type checks on every PR. |
| **2. Host & Kitchen Management** | Weeks 3–5 | Host onboarding, listing CRUD, compliance workflows. | ✅ Host profile creation and editing flows complete.<br>✅ Kitchens CRUD API + React management UI shipped with photo upload to object storage (Supabase or S3-compatible).<br>✅ Health certificate upload stored and flagged for admin review with audit log.<br>✅ Admin panel supports manual approval/rejection with notifications. |
| **3. Renter Discovery & Booking** | Weeks 6–8 | Renter onboarding, search, availability, booking + payments intent. | ✅ Renter profile flow live with verification checks.<br>✅ Search index (PostgreSQL + PostGIS or Typesense) supports location, certification, and equipment filters.<br>✅ Availability service blocks double-booking and enforces buffer windows.<br>✅ Stripe Checkout flow completes test bookings and records payment intent + booking reservation. |
| **4. Payments, Polish & Launch** | Weeks 9–10 | Settlements, reviews, hardening, launch operations. | ✅ Stripe Connect custom accounts configured with onboarding UI for hosts.<br>✅ Booking completion triggers automatic payout flow and invoice email.<br>✅ Review/rating CRUD operational with abuse reporting.<br>✅ Launch checklist signed off (monitoring alerts, runbooks, on-call). |

---

## 2. Architecture & Environment

### 2.1 High-Level System Diagram

- **Frontend Web App (React + Vite + Tailwind):** Deployed to Cloudflare Pages, authenticated via JWT stored in httpOnly cookies, uses Zustand for session state, and hits backend APIs via `/api/*` reverse proxy.
- **Backend API (Node.js + Express):** Deployed on Fly.io with Docker; exposes REST endpoints documented in `contracts/openapi.yaml`. Services include `auth`, `listing`, `availability`, `booking`, `payments`, and `admin`.
- **Database:** PostgreSQL 15 (Supabase managed) with schemas for `users`, `kitchens`, `documents`, `availability_slots`, `bookings`, `payments`, and `reviews`.
- **Cache & Queues:** Redis for rate limiting, session invalidation, and storing temporary availability locks. BullMQ handles asynchronous jobs (email, payout retries, document virus scanning).
- **File Storage:** Supabase Storage (S3-compatible) buckets for kitchen photos and compliance documents with signed URL access and antivirus scanning via ClamAV Lambda.
- **Observability:** Sentry for error tracking, OpenTelemetry traces exported to Honeycomb, and Grafana Cloud for dashboards + uptime checks.

### 2.2 Environment Strategy

| Environment | Purpose | Branch | Notes |
| --- | --- | --- | --- |
| **Local** | Developer productivity. | Feature branches. | Docker Compose spins up PostgreSQL, Redis, mailhog, and MinIO (S3 mock). |
| **Staging** | QA sign-off, stakeholder demos. | `develop`. | Deploy via GitHub Actions to Fly.io and Cloudflare Pages with feature flag toggles. |
| **Production** | Public release. | `main`. | Require passing smoke tests + manual approval gate. |

---

## 3. Detailed Workstreams & Tasks

### 3.1 Authentication & Authorization

- Implement registration/login endpoints with bcrypt hashing and password strength validation (zxcvbn scoring).
- Issue short-lived access tokens and long-lived refresh tokens stored in HTTP-only cookies; rotate signing keys every 30 days using Fly secrets.
- Role-based access middleware (`Admin`, `Host`, `Renter`) and policy helpers (e.g., host owns kitchen resource).
- Email verification service using Resend API; include rate limiting and signed tokens expiring after 24 hours.
- Integrate Stripe Identity KYC webhook to flag hosts pending verification.

### 3.2 Host Experience

- Host onboarding wizard capturing kitchen address, hours, certifications, and payout readiness checklist.
- Kitchen listing CRUD endpoints with validation via Zod; React form wizard with optimistic UI.
- Photo upload flow using signed URLs and client-side compression (browser-image-compression) before upload.
- Compliance document storage tagged with expiration date; trigger reminder emails 30 days before expiry via scheduled job.
- Admin review queue with filterable table, bulk approve, and action history.

### 3.3 Renter Experience & Discovery

- Renter onboarding profile (business name, insurance proof upload, kitchen requirements).
- Search API with filters (location radius, equipment, certification level, availability window). Use PostgreSQL full-text search + PostGIS for geospatial radius.
- Availability calendar: import host operating hours, block-out windows, and integrate ICS export.
- Booking request modal that validates slot availability using Redis-backed distributed lock.
- Stripe Checkout session creation with metadata linking to booking ID; handle success/cancel webhooks.

### 3.4 Booking Lifecycle & Payments

- Booking statuses: `pending`, `confirmed`, `in_progress`, `completed`, `cancelled`. Cancellation policy logic for refund percentages.
- Pre-authorize renter card at booking confirmation; capture on completion or auto-capture at booking end time.
- Stripe Connect Custom for host payouts; store onboarding status and display progress tracker.
- Automatic payouts triggered by webhook once booking marked completed; retries handled via BullMQ queue.
- Finance ledger table storing debits/credits per party for audit compliance.

### 3.5 Reviews & Notifications

- Two-sided review system unlocking 24 hours after booking completion.
- Notification service using SendGrid/Resend templates and in-app toast events via WebSocket (Socket.IO) for booking updates.
- Abuse report workflow with admin triage and soft-delete capabilities.

### 3.6 Security & Compliance

- Enforce OWASP-recommended headers via Helmet middleware; CSP tuned for Cloudflare Pages assets.
- Regular dependency scanning using GitHub Dependabot and `npm audit` gate in CI.
- Store secrets in Fly.io secrets manager and Cloudflare Pages environment variables; prohibit storing secrets in repo.
- Document SOC 2-aligned controls for audit readiness; maintain runbook for data export/delete requests (GDPR/CCPA).

---

## 4. Testing & Quality Assurance

| Layer | Tooling | Coverage Targets |
| :--- | :--- | :--- |
| **Unit** | Jest (frontend + backend), React Testing Library | ≥80% coverage for critical modules (auth, booking, payments). |
| **Integration** | Supertest for REST APIs with database test containers; Stripe mock webhooks. | Cover happy path + edge cases for all Phase 2 and Phase 3 endpoints. |
| **End-to-End** | Playwright running against staging nightly. | Booking, payout, review flows succeed; screenshot diffs tracked. |
| **Static Analysis** | ESLint, Prettier, TypeScript strict mode, Zod runtime validation. | Lint/type-check on every push. |
| **Performance** | k6 smoke tests for booking endpoints; Lighthouse CI for PWA. | p95 booking request < 500ms; PWA performance score ≥ 85. |

Bug triage meets twice per week during Phases 3–4; Sev1 incidents require response within 1 hour and documented in incident log.

---

## 5. Data Model Snapshot

| Table | Key Columns | Notes |
| :--- | :--- | :--- |
| `users` | `id`, `role`, `email`, `password_hash`, `email_verified_at`, `stripe_customer_id` | Soft delete column for GDPR requests. |
| `hosts` | `user_id`, `kyc_status`, `stripe_account_id`, `business_name`, `phone` | `kyc_status` enumerations: `pending`, `approved`, `rejected`. |
| `kitchens` | `id`, `host_id`, `address`, `geo_point`, `base_rate_cents`, `amenities[]`, `status` | `status`: `draft`, `submitted`, `approved`, `rejected`, `suspended`. |
| `documents` | `id`, `kitchen_id`, `type`, `storage_path`, `expires_at`, `review_status` | Document types include `health_certificate`, `insurance`. |
| `availability_slots` | `kitchen_id`, `start_at`, `end_at`, `buffer_minutes`, `status` | Indexed for overlap detection. |
| `bookings` | `id`, `kitchen_id`, `renter_id`, `status`, `total_cents`, `payment_intent_id`, `payout_status` | Links to `payments` table for ledger entries. |
| `payments` | `id`, `booking_id`, `type`, `amount_cents`, `stripe_transfer_id`, `stripe_charge_id` | Types include `charge`, `refund`, `payout`. |
| `reviews` | `id`, `booking_id`, `author_id`, `target_type`, `rating`, `comment`, `moderation_status` | `target_type`: `host` or `renter`. |

---

## 6. DevOps & Tooling Checklist

1. **Repository Setup:** Monorepo using npm workspaces; `apps/web`, `services/*`, `packages/*` shared libs.
2. **CI/CD:** GitHub Actions workflow running lint, tests, build, and Docker image publishing. Separate workflow deploys to staging on merge into `develop` and production on manual approval from release manager.
3. **Secrets Management:** Use Doppler or 1Password for secret distribution; bootstrap Fly.io & Cloudflare Pages with environment variables via `doppler secrets upload`.
4. **Monitoring:** Configure Honeycomb dataset for API traces, Grafana dashboards for key metrics (booking conversion, Stripe failures, queue depth), and PagerDuty escalation for Sev1 incidents.
5. **Analytics:** PostHog for event tracking (search, booking funnel, cancellation reasons) with privacy consent banner handled via Cookiebot.
6. **Runbooks:** Document rollback procedures, Stripe webhook replay instructions, and compliance escalation steps in `/runbooks`.

---

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
| :--- | :--- | :--- |
| Stripe onboarding delays for hosts. | Blocks payout functionality at launch. | Provide pre-launch checklist, proactive support, and fallback manual payout script for first hosts. |
| Availability conflicts due to concurrency. | Double-bookings undermine trust. | Redis-based locking, automated reconciliation job, manual override tooling for ops. |
| Compliance document falsification. | Regulatory risk, platform suspension. | Integrate third-party validation (Certifi or similar) and manual spot checks; watermark approved docs. |
| Performance degradation under launch load. | Poor UX, failed bookings. | Load test with k6, auto-scale Fly.io machines, configure CDN caching for static assets. |
| Data privacy incidents. | Legal/brand damage. | Least-privilege DB roles, regular access reviews, encrypted backups, incident response playbook. |

---

## 8. Launch Readiness Checklist

- [ ] Complete end-to-end dry run: host onboarding → listing approval → renter booking → payout.
- [ ] Run accessibility audit (axe + manual) and remediate WCAG 2.1 AA blockers.
- [ ] Finalize Terms of Service, Privacy Policy, and acceptable use guidelines.
- [ ] Populate platform with 10 vetted launch kitchens and seed renter accounts for smoke testing.
- [ ] Train support staff and provide canned responses for top 10 expected issues.
- [ ] Schedule production readiness review and sign-off from security, legal, and product.

---

## 9. Post-MVP Roadmap Highlights

- **v1.1 (Month 3):** Loyalty incentives, automated invoice exports to QuickBooks, SMS reminders via Twilio.
- **v1.2 (Month 4):** Smart matching suggestions using renter preferences and availability scoring; expand to Canadian provinces (evaluate GST implications).
- **v1.3 (Month 6):** Mobile companion app (React Native) for host calendar management, push notifications via Expo.
- **v2.0 (Month 9+):** AI-powered pricing recommendations, Kitchen Cam integrations, enterprise API product for franchisors.

---

## 10. Immediate Next Steps (Week 0)

1. Confirm architecture decisions with CTO and document any deviations in `docs/decisions/adr-001-foundation.md`.
2. Stand up initial Supabase project and apply base migrations (`prepchef/db/schema.sql`).
3. Configure GitHub Actions secrets for Cloudflare Pages, Fly.io, Stripe, Supabase, Resend, and PostHog.
4. Create shared UI component library package (`packages/ui`) with Tailwind preset and Storybook.
5. Draft customer support SOP and escalation matrix in `operations/support_playbook.md`.

