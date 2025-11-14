# Growth Alpha Initiative Epics

This document captures the prioritized epics and issue outlines for the Growth Alpha initiatives. Each epic summarizes the objectives, labels, and linked issues scoped for delivery.

## Referral System Launch

**Description:** Implement referral invitations that award credits after verified bookings, connect onboarding with invite codes, and surface referral-to-revenue metrics.

**Labels:** `growth-alpha`, `referrals`, `priority-week1`

### Issues

1. **Design referral data model and migrations** (`backend`, `database`, `migration`)
   - Create `migrations/00X_referrals.sql` with tables for referral codes, invitations, and credit ledger.
   - Add indices for fast lookup by `maker_id`, `host_id`, and `ref_code`.
   - Document ERD updates in `docs/`.
   - _Acceptance:_ Migration applies cleanly on staging snapshot; schema matches analytics requirements for Grafana funnel.

2. **Build `/api/referrals/` endpoints** (`backend`, `api`, `python`)
   - Implement POST for referral code creation, GET for status, and instrumentation hooks.
   - Validate invitee eligibility and idempotency on repeated submissions.
   - Add unit and integration tests via `pytest`.
   - _Acceptance:_ Test suite covers 1 credit per unique referred booking; endpoints logged in metrics pipeline.

3. **Implement referral verification worker** (`backend`, `async-jobs`, `analytics`)
   - Add `jobs/referral_worker.py` to confirm booking completion, issue credits, and trigger SendGrid template.
   - Read credit value from environment configuration and emit analytics events on success/failure.
   - _Acceptance:_ Worker handles retries with dead-letter queue; credits appear in ledger and Grafana funnel.

4. **Add invite code to onboarding flow** (`frontend`, `react`, `growth-exp`)
   - Update `apps/onboarding/**` UI with optional invite code field and contextual tooltip.
   - Persist invite code to API, handling invalid or expired codes gracefully.
   - Ensure the A/B flag is ready for growth experiments and fire events for invite submission and failure states.
   - _Acceptance:_ UX validated in cross-browser smoke test; events recorded for invite submission and failure states.

## Promo Codes & Discount Engine

**Description:** Deliver marketing-grade promo management, eligibility rules, and price recalculation.

**Labels:** `growth-alpha`, `promos`, `priority-week1`

### Issues

1. **Model promos and discounts in database** (`backend`, `database`, `migration`)
   - Author `migrations/00X_promos.sql` with tables for promo definitions, eligibility constraints, and usage logs.
   - Support percentage and fixed-amount discounts, expirations, and usage caps.
   - _Acceptance:_ Migration reversible and covered by schema tests; data model supports city and campaign tagging.

2. **Implement `/api/promos/` CRUD and validation** (`backend`, `api`, `python`)
   - Secure endpoints for creating, updating, pausing, and expiring promo codes.
   - Enforce eligibility checks for first-time makers, city, and campaign tag.
   - Emit analytics events on creation and redemption.
   - _Acceptance:_ Booking pipeline recalculates totals with active promos; unit tests confirm usage limits and expirations.

3. **Integrate promo application in pricing service** (`services`, `python`, `pricing`)
   - Extend `pricing-service/apply_promos.py` to stack eligible promos, resolve precedence, and return discount breakdowns.
   - Add coverage for conflicting promos and edge cases.
   - _Acceptance:_ Pricing regression suite passes with promo scenarios; logs expose promo IDs for analytics correlation.

4. **Admin dashboard for promo management** (`frontend`, `admin`, `typescript`)
   - Build `apps/admin/promos.tsx` with table, filters, and create/edit forms.
   - Include status toggles, usage stats, and audit trail display.
   - _Acceptance:_ Admin can create, pause, and expire promos end-to-end; frontend tests (Jest/Playwright) cover CRUD happy paths.

## Kitchen Discovery Experience

**Description:** Ship the first discoverability layer with search, filters, and visual browsing.

**Labels:** `growth-alpha`, `discovery`, `priority-week2`

### Issues

1. **Seed discovery data and assets** (`data`, `tooling`)
   - Populate `data/seed_kitchens_photos.json` with curated inventory and S3 paths or placeholders.
   - Script data loading for development and staging environments.
   - _Acceptance:_ Seed script idempotent and documented; asset checks confirm 404 fallback handling.

2. **Implement kitchen search API** (`backend`, `search`, `python`)
   - Create `api/search/kitchens.py` supporting query `k`, filters (price/hour, permitted uses, availability), and pagination.
   - Optimize for <500 ms response via indexing or caching.
   - _Acceptance:_ Load tests confirm SLA under expected traffic; results integrated with analytics logging.

3. **Build discovery React grid and filters** (`frontend`, `react`, `ux`)
   - Scaffold `apps/discover/` pages with responsive card grid, filter drawer, and lazy-loaded photos.
   - Target Lighthouse desktop score >90, ensuring accessibility (keyboard navigation, alt text).
   - _Acceptance:_ End-to-end smoke tests with sample data; accessibility checklist completed.

## Maker Portfolio Pages

**Description:** Provide portfolio showcases with uploads, categories, badges, and caching.

**Labels:** `growth-alpha`, `maker-experience`, `priority-week2`

### Issues

1. **Design portfolio API and caching** (`backend`, `api`, `caching`)
   - Implement `api/makers/portfolio.py` for CRUD, category tagging, certifications, and reviews feed.
   - Add Cloudflare cache headers (30 min TTL) for public GET and verify auth/role checks.
   - _Acceptance:_ Cache hit-rate tracked in analytics; auth and role checks verified.

2. **Build maker portfolio frontend** (`frontend`, `react`)
   - Create `apps/maker/[maker_id]/index.tsx` with gallery, product sections, badges, and reviews.
   - Support lazy loading and skeleton states with responsive layouts across desktop and mobile.
   - _Acceptance:_ Integration tests cover data fetching states; responsive layout validated on key breakpoints.

3. **Integrate secure media uploads** (`backend`, `integrations`, `security`)
   - Extend `integrations/cloud_uploads.py` for authenticated uploads up to 50 MB, virus scanning hook, and presigned URLs.
   - Connect upload flow to portfolio management UI and enforce file size/type validation.
   - _Acceptance:_ Monitoring alerts for upload failures; validations prevent disallowed files.

## Analytics & Metrics Foundation

**Description:** Establish event schema, pipeline, and admin visibility for conversion metrics.

**Labels:** `growth-alpha`, `analytics`, `priority-week3`

### Issues

1. **Define analytics schema and migrations** (`analytics`, `database`)
   - Author `analytics/schema.sql` with event tables, staging buffers, and retention policies.
   - Ensure compatibility with Grafana dashboards and document the event taxonomy.
   - _Acceptance:_ Schema validated via dbt/SQL tests (if available); documentation outlines taxonomy.

2. **Implement events pipeline service** (`backend`, `analytics`, `observability`)
   - Build `analytics/events_pipeline.py` to ingest, validate, batch, and forward events with >99% success rate.
   - Add retry/backoff handling and dead-letter queue; export metrics to monitoring stack.
   - _Acceptance:_ Load test ensures throughput under peak booking traffic; monitoring reflects pipeline health.

3. **Admin analytics dashboard** (`frontend`, `admin`, `analytics`)
   - Develop `apps/admin/analytics.tsx` showing funnels (onboarding → booking → payout), referrals, and promo usage.
   - Include date filters, cohort toggles, and export capabilities referencing consistent Grafana metrics.
   - _Acceptance:_ Dashboard matches sample data scenarios; Grafana tiles align with dashboard metrics.

## Feedback & Rating System

**Description:** Collect and moderate post-booking ratings with abuse filtering and admin controls.

**Labels:** `growth-alpha`, `trust-safety`, `priority-week3`

### Issues

1. **Create ratings schema and constraints** (`backend`, `database`, `migration`)
   - Implement `migrations/00X_ratings.sql` for 1–5 stars, comments, booking linkage, and moderation flags.
   - Ensure duplicate submissions are blocked at the DB level and weighted average view logic is codified.
   - _Acceptance:_ Constraints enforce uniqueness; reporting view provides weighted averages.

2. **Develop `/api/ratings/` service** (`backend`, `api`, `trust-safety`)
   - Enforce one rating per booking, sentiment analysis/keyword filtering for abuse detection, and event emission for analytics.
   - Provide admin override endpoints with auditing.
   - _Acceptance:_ Unit tests cover abuse flagging and admin override; admin removal endpoints audited.

3. **Implement reviews UI & modal flow** (`frontend`, `react`, `ux`)
   - Build `apps/reviews/` modal triggered post-booking with success and decline states.
   - Surface aggregated ratings once there are at least three reviews, ensuring accessibility compliance.
   - _Acceptance:_ UX validated across desktop/mobile; accessibility review completed.

## Email & Push Engagement Engine

**Description:** Launch lifecycle messaging across email and push with opt-out compliance.

**Labels:** `growth-alpha`, `engagement`, `priority-week4`

### Issues

1. **Integrate SendGrid client** (`backend`, `integrations`, `email`)
   - Implement `integrations/sendgrid_client.py` with templated campaigns, bounce tracking (<0.5% sandbox), and unsubscribe handling.
   - _Acceptance:_ Email logs visible in monitoring dashboard; opt-out flow tested end-to-end.

2. **Implement digest worker for campaigns** (`backend`, `async-jobs`)
   - Create `jobs/digest_worker.py` scheduling “Next booking,” “Invite friend,” and “New review” campaigns.
   - Pull dynamic content, throttle per user, and document cron schedule while emitting analytics events per send.
   - _Acceptance:_ Worker meets scheduling requirements; analytics events captured for sends.

3. **FCM push notification service** (`backend`, `mobile`, `notifications`)
   - Build `fcm/push_notifications.py` with device token registry, segmentation, and delivery tracking honoring notification preferences.
   - _Acceptance:_ Push receipts tracked, opt-outs honored; load tests ensure performance at scale.

## Legal & Tax Expansion Prep

**Description:** Ensure invoices, tax rules, and documentation support a multi-state rollout.

**Labels:** `growth-alpha`, `compliance`, `priority-week4`

### Issues

1. **Extend state tax rule engine** (`backend`, `compliance`, `tax`)
   - Update `regengine/extensions/state_tax_rules.py` with daily rate refresh, jurisdiction overrides, and monitoring for stale rates.
   - _Acceptance:_ Unit/integration tests cover representative states; rates auto-update without manual intervention.

2. **Generate tax-inclusive invoices** (`backend`, `pdf`, `billing`)
   - Implement `api/invoice/pdf_generator.py` producing compliant invoices per booking, including tax breakdown with localization hooks.
   - _Acceptance:_ Sample PDFs reviewed by compliance; documents stored securely with retention policy.

3. **Document tax compliance processes** (`docs`, `compliance`)
   - Draft `docs/tax_compliance.md` with procedures, state coverage, and audit trail references, linked from compliance playbooks.
   - _Acceptance:_ Legal team sign-off recorded; documentation accessible from compliance resources.
