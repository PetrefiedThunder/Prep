#!/usr/bin/env bash
# MVP Bootstrap Script
# Creates the "MVP OR BUST – Dec 7 2025" milestone and 10 linked issues
# Usage: ./scripts/bootstrap-mvp.sh

set -euo pipefail

MILESTONE_TITLE="MVP OR BUST – Dec 7 2025"
REPO="PetrefiedThunder/Prep"
DUE_DATE="2025-12-07"

echo "🚀 Bootstrapping MVP Milestone for ${REPO}"
echo "================================================"
echo ""

# Create milestone
echo "📍 Creating milestone: ${MILESTONE_TITLE}"
MILESTONE_DESC="Goal: A non-founder completes a real \$100+ booking in Stripe test mode, end-to-end, with zero manual intervention.

**Definition of Done (DoD):**
✅ Signup → Search → Book → Pay → Receipt runs in Playwright CI
✅ No mocks, no manual steps
✅ Only 3 services (FastAPI + Next.js + Postgres/Redis)
✅ Test coverage ≥55%, E2E pass rate ≥95%

**Owner:** @PetrefiedThunder
**Labels:** MVP, blocking, P0, ship-it"

gh milestone create "$MILESTONE_TITLE" \
  --repo "$REPO" \
  --due-date "$DUE_DATE" \
  --description "$MILESTONE_DESC" || {
    echo "⚠️  Milestone might already exist, continuing..."
  }

# Get milestone number
MILESTONE_NUM=$(gh milestone list --repo "$REPO" --json number,title | jq -r ".[] | select(.title==\"${MILESTONE_TITLE}\") | .number")

if [ -z "$MILESTONE_NUM" ]; then
  echo "❌ Failed to create or find milestone"
  exit 1
fi

echo "✅ Milestone #${MILESTONE_NUM} ready"
echo ""

# Issue #1: README and Repo Hygiene (P0)
echo "📝 Creating Issue #1: README and Repo Hygiene"
gh issue create --repo "$REPO" \
  --title "README and Repo Hygiene (P0)" \
  --milestone "$MILESTONE_NUM" \
  --label "P0,MVP,blocking,documentation" \
  --assignee "PetrefiedThunder" \
  --body "## 🎯 Objective
Clean up repository conflicts, duplicate documentation, and establish proper CI badges.

## 📋 Tasks
- [ ] Remove all \`<<<<<<<\`, \`=======\`, \`>>>>>>>\` conflict markers
- [ ] Collapse duplicate 'Current State' blocks → 'Current State – Nov 23 2025'
- [ ] Add CI badges: Build ✔ | E2E | Coverage | Last Update
- [ ] Move legacy bug reports → \`docs/archive/2025-11/\`

## ✅ Acceptance Criteria
- \`git grep -n '<<<<<<< HEAD'\` returns 0 results
- \`git grep -n '======='\` (conflict markers only) returns 0 results
- README renders cleanly and passes markdown-lint
- CI badge links are live and functional
- All legacy issues archived with timestamp

## 🔗 Related
Part of **MVP OR BUST – Dec 7 2025** milestone
Blocks: #3, #5, #9

## 📊 Priority
**P0** - Must complete before MVP launch"

# Issue #2: Collapse to 3 Core Services (P0)
echo "📝 Creating Issue #2: Collapse to 3 Core Services"
gh issue create --repo "$REPO" \
  --title "Collapse to 3 Core Services (P0)" \
  --milestone "$MILESTONE_NUM" \
  --label "P0,MVP,blocking,infrastructure" \
  --assignee "PetrefiedThunder" \
  --body "## 🎯 Objective
Simplify infrastructure to exactly 3 core services for MVP: FastAPI Gateway, Next.js Frontend, Postgres+Redis.

## 🔧 Keep
- \`api/\` (FastAPI Gateway)
- \`apps/harborhomes/\` (Next.js frontend)
- Postgres + Redis (in docker-compose)

## 🗑️ Archive
- All \`prepchef/services/*\`
- Worker queues
- OCR services
- Neo4j adapters
- Vendor verification services

## 📋 Tasks
- [ ] Move archived services to \`archive/prepchef-services/\`
- [ ] Update \`docker-compose.yml\` to only run 3 containers
- [ ] Remove references in \`Makefile\`
- [ ] Update service discovery / health checks
- [ ] Update README architecture diagram

## ✅ Acceptance Criteria
- \`docker-compose up\` runs exactly 3 containers
- \`make health\` passes for all 3 services
- No broken imports or service references
- Documentation reflects new architecture

## 🔗 Related
Part of **MVP OR BUST – Dec 7 2025** milestone
Blocks: #3, #6

## 📊 Priority
**P0** - Critical path blocker"

# Issue #3: Implement Six Real Endpoints (P0)
echo "📝 Creating Issue #3: Implement Six Real Endpoints"
gh issue create --repo "$REPO" \
  --title "Implement Six Real Endpoints (P0)" \
  --milestone "$MILESTONE_NUM" \
  --label "P0,MVP,blocking,backend,api" \
  --assignee "PetrefiedThunder" \
  --body "## 🎯 Objective
Build the 6 core API endpoints required for the MVP booking flow with proper error handling, security, and concurrency control.

## 🛣️ Endpoints to Implement

### 1. \`POST /auth/signup\`
- Create new user account
- Hash password with bcrypt
- Return JWT token

### 2. \`POST /auth/login\`
- Validate credentials
- Return JWT token
- Track last login timestamp

### 3. \`GET /kitchens?lat,lng,from,to\`
- PostGIS radius search
- Filter by availability window
- Return kitchen details + hourly rates

### 4. \`POST /bookings\`
- Create booking hold
- Acquire Redis lock (key: \`booking:{kitchen_id}:{date}:{hour}\`)
- Return booking ID + payment intent

### 5. \`POST /payments/intent\`
- Create Stripe PaymentIntent (test mode)
- Link to booking ID
- Return client secret

### 6. \`POST /webhooks/stripe\`
- Verify webhook signature
- Handle \`payment_intent.succeeded\`
- Mark booking as \`confirmed\`
- Release Redis lock

### 7. \`GET /bookings/:id\`
- Return booking receipt
- Include kitchen details, timestamps, payment status

## 📋 Tasks
- [ ] Implement all 7 endpoints in \`api/routes/\`
- [ ] Add Pydantic schemas for request/response
- [ ] Add Redis locking with TTL (15 min)
- [ ] Integrate Stripe SDK (test mode keys)
- [ ] Verify webhook signatures (Stripe signing secret)
- [ ] Add pytest tests for each endpoint
- [ ] Add mypy strict type checking
- [ ] Create concurrency test (50 parallel bookings → 1 success, 49 conflict)

## ✅ Acceptance Criteria
- All endpoints covered by pytest
- mypy --strict passes
- Stripe webhook signature verification works
- Concurrency test: 1 booking succeeds, 49 get 409 Conflict
- No hardcoded secrets (use env vars)
- OpenAPI docs auto-generated

## 🔗 Related
Part of **MVP OR BUST – Dec 7 2025** milestone
Depends on: #2
Blocks: #5, #6

## 📊 Priority
**P0** - Core MVP functionality"

# Issue #4: Seed Realistic Kitchen Data (P1)
echo "📝 Creating Issue #4: Seed Realistic Kitchen Data"
gh issue create --repo "$REPO" \
  --title "Seed Realistic Kitchen Data (P1)" \
  --milestone "$MILESTONE_NUM" \
  --label "P1,MVP,database,seed-data" \
  --assignee "PetrefiedThunder" \
  --body "## 🎯 Objective
Populate database with 5 realistic San Francisco commercial kitchen listings for MVP demo.

## 📊 Data Requirements

### Kitchens (5 listings)
- Real SF addresses (use test addresses, not real businesses)
- Hourly rates: \$100–\$300/hr (10000–30000 cents)
- PostGIS geometry (latitude/longitude)
- Kitchen amenities (ovens, stoves, prep space)
- Photos (placeholder URLs or local assets)

### Availability
- Next 14 days from today
- 9 AM – 9 PM daily
- Generate availability slots in \`kitchen_availability\` table

## 📋 Tasks
- [ ] Create Alembic migration for seed data
- [ ] Add 5 kitchen records with SF addresses
- [ ] Generate 14-day availability (9 AM–9 PM)
- [ ] Populate PostGIS \`geom\` column
- [ ] Add kitchen amenities/photos
- [ ] Verify data via SQL queries

## ✅ Acceptance Criteria
- \`SELECT COUNT(*) FROM kitchens\` returns 5
- All \`geom\` columns are non-null
- \`GET /kitchens?lat=37.7749&lng=-122.4194\` returns results
- Availability covers next 14 days
- Migration runs cleanly on fresh DB

## 🔗 Related
Part of **MVP OR BUST – Dec 7 2025** milestone
Blocks: #5, #6

## 📊 Priority
**P1** - Required for realistic demo"

# Issue #5: Frontend Wiring / Mock Removal (P0)
echo "📝 Creating Issue #5: Frontend Wiring / Mock Removal"
gh issue create --repo "$REPO" \
  --title "Frontend Wiring / Mock Removal (P0)" \
  --milestone "$MILESTONE_NUM" \
  --label "P0,MVP,blocking,frontend" \
  --assignee "PetrefiedThunder" \
  --body "## 🎯 Objective
Replace all mock data with real API calls and implement complete user flow from signup to receipt.

## 🗑️ Remove
- All files in \`apps/harborhomes/mockData*\`
- Any hardcoded test data in components
- Mock API responses

## 🛣️ Pages to Implement

### 1. \`/signup\`
- Email, password, name fields
- Call \`POST /auth/signup\`
- Store JWT in httpOnly cookie or localStorage
- Redirect to \`/search\`

### 2. \`/login\`
- Email, password fields
- Call \`POST /auth/login\`
- Store JWT
- Redirect to \`/search\`

### 3. \`/search\`
- Map view (Mapbox/Leaflet)
- Date/time picker (from/to)
- Call \`GET /kitchens?lat,lng,from,to\`
- Display kitchen cards

### 4. \`/kitchen/[id]\`
- Kitchen details
- Availability calendar
- \"Book Now\" button → \`/checkout\`

### 5. \`/checkout\`
- Booking summary
- Stripe Elements (card input)
- Call \`POST /payments/intent\`
- Submit payment → Redirect to \`/bookings/[id]\`

### 6. \`/bookings/[id]\`
- Receipt page
- Booking details, payment status
- Call \`GET /bookings/:id\`

## 📋 Tasks
- [ ] Delete all mock data files
- [ ] Set up SWR or React Query for API calls
- [ ] Implement all 6 pages
- [ ] Add Stripe Elements for checkout
- [ ] Use test card \`4242 4242 4242 4242\`
- [ ] Add loading states and error handling
- [ ] Add authentication guards (redirect if not logged in)

## ✅ Acceptance Criteria
- Manual demo completes full flow locally
- No mock data remains in codebase
- \`grep -r 'mockData' apps/harborhomes\` returns 0 results
- Stripe test payment succeeds
- All pages render without console errors

## 🔗 Related
Part of **MVP OR BUST – Dec 7 2025** milestone
Depends on: #3, #4
Blocks: #6

## 📊 Priority
**P0** - Critical for MVP demo"

# Issue #6: End-to-End E2E Pipeline (P0)
echo "📝 Creating Issue #6: End-to-End E2E Pipeline"
gh issue create --repo "$REPO" \
  --title "End-to-End E2E Pipeline (P0)" \
  --milestone "$MILESTONE_NUM" \
  --label "P0,MVP,blocking,testing,e2e" \
  --assignee "PetrefiedThunder" \
  --body "## 🎯 Objective
Implement comprehensive E2E and integration tests covering the full booking flow and edge cases.

## 🧪 Playwright E2E: \`tests/e2e/HappyPath.spec.ts\`

### Test Flow
1. Navigate to \`/signup\`
2. Create account with unique email
3. Verify redirect to \`/search\`
4. Enter SF coordinates + next week date range
5. Click first kitchen result
6. Click \"Book Now\"
7. Fill Stripe test card \`4242 4242 4242 4242\`
8. Submit payment
9. Verify redirect to \`/bookings/[id]\`
10. Assert booking status = \"confirmed\"
11. Assert kitchen name displayed
12. Assert total price matches

## 🧪 Pytest Integration Tests

### \`tests/concurrency/test_booking_race.py\`
- Spawn 50 parallel requests to \`POST /bookings\`
- Same kitchen, same timeslot
- Assert: 1 succeeds (201), 49 fail (409 Conflict)

### \`tests/webhooks/test_stripe_webhook.py\`
- Mock Stripe webhook payload
- Verify signature validation
- Assert booking status updated to \"confirmed\"
- Assert idempotency (replay same webhook → no duplicate)

## 📋 Tasks
- [ ] Set up Playwright in \`tests/e2e/\`
- [ ] Write \`HappyPath.spec.ts\`
- [ ] Add Playwright to CI pipeline
- [ ] Write \`test_booking_race.py\`
- [ ] Write \`test_stripe_webhook.py\`
- [ ] Add performance assertion: p95 booking latency < 800ms
- [ ] Configure CI to require E2E pass before merge

## ✅ Acceptance Criteria
- Playwright test passes locally and in CI
- Concurrency test: 1 success, 49 conflicts
- Webhook replay test prevents duplicates
- CI blocks merge if E2E fails
- p95 booking create < 800ms

## 🔗 Related
Part of **MVP OR BUST – Dec 7 2025** milestone
Depends on: #5
Blocks: #9

## 📊 Priority
**P0** - Quality gate for MVP"

# Issue #7: Security Gates and Linters (P1)
echo "📝 Creating Issue #7: Security Gates and Linters"
gh issue create --repo "$REPO" \
  --title "Security Gates and Linters (P1)" \
  --milestone "$MILESTONE_NUM" \
  --label "P1,MVP,security,ci-cd" \
  --assignee "PetrefiedThunder" \
  --body "## 🎯 Objective
Add automated security checks and linting rules to prevent common vulnerabilities and code quality issues.

## 🔒 Security Checks

### 1. Conflict Marker Detection
- Fail CI if \`<<<<<<<\`, \`=======\`, \`>>>>>>>\` found
- Add to \`make quality-check\`

### 2. Secret Scanning
- Install Gitleaks or TruffleHog
- Allowlist \`.env.example\`, \`*.test.ts\`
- Fail CI on hardcoded secrets

### 3. HTTP Timeout Validation
- Custom ruff/eslint rule
- Fail on \`requests.get()\` without timeout
- Fail on \`fetch()\` without AbortSignal

### 4. Idempotency Key Validation
- Unit tests for \`POST /bookings\`
- Same idempotency key → 200 (cached response)
- Different key, same data → 409 Conflict

## 📋 Tasks
- [ ] Add conflict marker check to CI
- [ ] Install Gitleaks, configure allowlist
- [ ] Create custom ruff rule for HTTP timeout
- [ ] Create custom eslint rule for fetch timeout
- [ ] Write idempotency key tests
- [ ] Update \`make quality-check\` to run all gates
- [ ] Document in \`CONTRIBUTING.md\`

## ✅ Acceptance Criteria
- CI runs \`make quality-check\` → all checks pass
- No false positives on allowlisted files
- Idempotency tests cover edge cases
- Documentation updated with new rules

## 🔗 Related
Part of **MVP OR BUST – Dec 7 2025** milestone

## 📊 Priority
**P1** - Prevents security regressions"

# Issue #8: Metrics & KPIs Dashboard (P2)
echo "📝 Creating Issue #8: Metrics & KPIs Dashboard"
gh issue create --repo "$REPO" \
  --title "Metrics & KPIs Dashboard (P2)" \
  --milestone "$MILESTONE_NUM" \
  --label "P2,MVP,observability,metrics" \
  --assignee "PetrefiedThunder" \
  --body "## 🎯 Objective
Set up Prometheus metrics and Grafana dashboard to monitor MVP health and performance.

## 📊 Metrics to Expose

### Application Metrics
- \`e2e_test_pass_rate\` (gauge, 0-100%)
- \`booking_create_latency_ms\` (histogram, p50/p95/p99)
- \`booking_conflict_count\` (counter)
- \`stripe_webhook_success_rate\` (gauge)
- \`active_bookings_count\` (gauge)

### Infrastructure Metrics
- API response time (per endpoint)
- Database connection pool usage
- Redis cache hit rate

## 📋 Tasks
- [ ] Add Prometheus exporter to FastAPI (\`/metrics\` endpoint)
- [ ] Instrument booking endpoints
- [ ] Set up Grafana in \`docker-compose.yml\`
- [ ] Create dashboard with 4 panels: E2E pass rate, booking latency, conflict count, webhook success
- [ ] Export dashboard JSON to \`observability/grafana-dashboard.json\`
- [ ] Add screenshot to README
- [ ] Add \`make monitor\` command

## ✅ Acceptance Criteria
- \`make monitor\` launches Grafana at localhost:3000
- Dashboard displays real-time metrics
- README includes dashboard screenshot
- Metrics survive service restarts

## 🔗 Related
Part of **MVP OR BUST – Dec 7 2025** milestone

## 📊 Priority
**P2** - Nice-to-have for MVP, critical post-launch"

# Issue #9: Squash & Tag Release (P0)
echo "📝 Creating Issue #9: Squash & Tag Release"
gh issue create --repo "$REPO" \
  --title "Squash & Tag Release (P0)" \
  --milestone "$MILESTONE_NUM" \
  --label "P0,MVP,blocking,release" \
  --assignee "PetrefiedThunder" \
  --body "## 🎯 Objective
Clean up commit history and tag the MVP release candidate.

## 🔄 Squash Strategy

### Combine micro-commits into 4 logical commits:
1. **lint-zero**: All linting, formatting, type fixes
2. **security-zero**: Conflict removal, secret scanning, idempotency
3. **docs-archive**: README cleanup, legacy docs moved
4. **infra-collapse**: Service consolidation, docker-compose simplification

## 📋 Tasks
- [ ] Review commit history since last tag
- [ ] Interactive rebase to squash into 4 commits
- [ ] Ensure each commit message follows conventional commits
- [ ] Tag \`v0.3.0-mvp-candidate\`
- [ ] Update \`RELEASE_NOTES.md\`
- [ ] Push tag to origin
- [ ] Verify tag builds successfully in CI

## ✅ Acceptance Criteria
- Main branch history < 100 commits (or reasonable number)
- Tag \`v0.3.0-mvp-candidate\` exists
- Tag builds successfully in CI
- \`RELEASE_NOTES.md\` documents all changes
- No broken references after squash

## 🔗 Related
Part of **MVP OR BUST – Dec 7 2025** milestone
Depends on: #6

## 📊 Priority
**P0** - Final step before MVP launch

## ⚠️ Warning
This rewrites git history. Coordinate with team before executing."

# Issue #10: Post-MVP Plan (P2)
echo "📝 Creating Issue #10: Post-MVP Plan"
gh issue create --repo "$REPO" \
  --title "Post-MVP Plan (P2)" \
  --milestone "$MILESTONE_NUM" \
  --label "P2,MVP,planning,post-launch" \
  --assignee "PetrefiedThunder" \
  --body "## 🎯 Objective
Define the roadmap for the first 30 days after MVP launch.

## 🚀 Post-MVP Initiatives

### Phase 1: Real Kitchen Onboarding (Days 1-7)
- [ ] Manually onboard 3 real SF commercial kitchens
- [ ] Collect real photos, amenities, pricing
- [ ] Verify insurance/compliance docs
- [ ] Update seed data with real listings

### Phase 2: Dogfooding (Days 8-14)
- [ ] Team members make daily test bookings
- [ ] Log UX friction points
- [ ] Track conversion funnel dropoff
- [ ] Gather qualitative feedback

### Phase 3: Compliance Queue (Days 15-21)
- [ ] Build manual admin panel for compliance review
- [ ] Add upload for insurance certs
- [ ] Add business permit verification
- [ ] Create approval workflow

### Phase 4: Service Re-evaluation (Days 22-30)
- [ ] Analyze booking volume and concurrency patterns
- [ ] Decide if booking service should be split
- [ ] Decide if we need worker queues
- [ ] Plan next architecture iteration

## 📋 Tasks
- [ ] Create Notion/Linear board for post-MVP tracking
- [ ] Schedule weekly retros
- [ ] Set up error tracking (Sentry)
- [ ] Set up analytics (PostHog/Mixpanel)

## ✅ Acceptance Criteria
- 3 real kitchens onboarded
- 10+ dogfood bookings completed
- Compliance queue designed (not necessarily built)
- Post-MVP roadmap documented

## 🔗 Related
Part of **MVP OR BUST – Dec 7 2025** milestone

## 📊 Priority
**P2** - Planning only, execution after MVP ships"

echo ""
echo "================================================"
echo "✅ Milestone created: ${MILESTONE_TITLE}"
echo "🚀 10 issues generated and assigned"
echo "🧩 All issues linked to milestone #${MILESTONE_NUM}"
echo "🕒 Target: Dec 7 2025 23:59 PT"
echo ""
echo "Next steps:"
echo "1. Review issues at: https://github.com/${REPO}/milestone/${MILESTONE_NUM}"
echo "2. Prioritize P0 issues first"
echo "3. Start with Issue #1 (README cleanup)"
echo ""
echo "🎯 No excuses. Just ship."
echo "================================================"
