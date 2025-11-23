#!/usr/bin/env python3
"""
MVP Bootstrap Script
Creates the "MVP OR BUST – Dec 7 2025" milestone and 10 linked issues using GitHub API
Usage: python scripts/bootstrap_mvp.py [GITHUB_TOKEN]
"""

import os
import sys
import json
from typing import Dict, List, Optional
from datetime import datetime
import urllib.request
import urllib.error

REPO_OWNER = "PetrefiedThunder"
REPO_NAME = "Prep"
MILESTONE_TITLE = "MVP OR BUST – Dec 7 2025"
DUE_DATE = "2025-12-07T23:59:59Z"


def github_api_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict] = None,
    token: Optional[str] = None
) -> Dict:
    """Make a GitHub API request."""
    url = f"https://api.github.com{endpoint}"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    req_data = json.dumps(data).encode('utf-8') if data else None
    request = urllib.request.Request(url, data=req_data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"❌ API Error ({e.code}): {error_body}")
        raise


def create_milestone(token: str) -> int:
    """Create the MVP milestone and return its number."""
    print(f"📍 Creating milestone: {MILESTONE_TITLE}")

    milestone_desc = """Goal: A non-founder completes a real $100+ booking in Stripe test mode, end-to-end, with zero manual intervention.

**Definition of Done (DoD):**
✅ Signup → Search → Book → Pay → Receipt runs in Playwright CI
✅ No mocks, no manual steps
✅ Only 3 services (FastAPI + Next.js + Postgres/Redis)
✅ Test coverage ≥55%, E2E pass rate ≥95%

**Owner:** @PetrefiedThunder
**Labels:** MVP, blocking, P0, ship-it"""

    data = {
        "title": MILESTONE_TITLE,
        "description": milestone_desc,
        "due_on": DUE_DATE,
        "state": "open"
    }

    # Try to create milestone
    try:
        result = github_api_request(
            f"/repos/{REPO_OWNER}/{REPO_NAME}/milestones",
            method="POST",
            data=data,
            token=token
        )
        milestone_num = result["number"]
        print(f"✅ Milestone #{milestone_num} created")
        return milestone_num
    except urllib.error.HTTPError as e:
        if e.code == 422:
            # Milestone might already exist, try to find it
            print("⚠️  Milestone might already exist, searching...")
            milestones = github_api_request(
                f"/repos/{REPO_OWNER}/{REPO_NAME}/milestones",
                token=token
            )
            for milestone in milestones:
                if milestone["title"] == MILESTONE_TITLE:
                    milestone_num = milestone["number"]
                    print(f"✅ Found existing milestone #{milestone_num}")
                    return milestone_num
        raise


def create_issue(
    token: str,
    title: str,
    body: str,
    labels: List[str],
    milestone_num: int
) -> Dict:
    """Create a GitHub issue."""
    print(f"📝 Creating: {title}")

    data = {
        "title": title,
        "body": body,
        "labels": labels,
        "milestone": milestone_num,
        "assignees": ["PetrefiedThunder"]
    }

    result = github_api_request(
        f"/repos/{REPO_OWNER}/{REPO_NAME}/issues",
        method="POST",
        data=data,
        token=token
    )

    print(f"   ✅ Issue #{result['number']}: {result['html_url']}")
    return result


def main():
    """Main execution."""
    print("🚀 Bootstrapping MVP Milestone for PetrefiedThunder/Prep")
    print("=" * 60)
    print()

    # Get GitHub token
    token = None
    if len(sys.argv) > 1:
        token = sys.argv[1]
    else:
        token = os.environ.get("GITHUB_TOKEN")

    if not token:
        print("❌ Error: GitHub token required")
        print()
        print("Usage:")
        print("  python scripts/bootstrap_mvp.py YOUR_GITHUB_TOKEN")
        print("  OR")
        print("  export GITHUB_TOKEN=your_token")
        print("  python scripts/bootstrap_mvp.py")
        print()
        print("Create a token at: https://github.com/settings/tokens/new")
        print("Required scopes: repo (full control)")
        sys.exit(1)

    try:
        # Create milestone
        milestone_num = create_milestone(token)
        print()

        # Track created issues
        created_issues = []

        # Issue #1: README and Repo Hygiene (P0)
        issue = create_issue(
            token=token,
            title="README and Repo Hygiene (P0)",
            labels=["P0", "MVP", "blocking", "documentation"],
            milestone_num=milestone_num,
            body="""## 🎯 Objective
Clean up repository conflicts, duplicate documentation, and establish proper CI badges.

## 📋 Tasks
- [ ] Remove all `<<<<<<<`, `=======`, `>>>>>>>` conflict markers
- [ ] Collapse duplicate 'Current State' blocks → 'Current State – Nov 23 2025'
- [ ] Add CI badges: Build ✔ | E2E | Coverage | Last Update
- [ ] Move legacy bug reports → `docs/archive/2025-11/`

## ✅ Acceptance Criteria
- `git grep -n '<<<<<<< HEAD'` returns 0 results
- `git grep -n '======='` (conflict markers only) returns 0 results
- README renders cleanly and passes markdown-lint
- CI badge links are live and functional
- All legacy issues archived with timestamp

## 🔗 Related
Part of **MVP OR BUST – Dec 7 2025** milestone
Blocks: #3, #5, #9

## 📊 Priority
**P0** - Must complete before MVP launch"""
        )
        created_issues.append(issue)

        # Issue #2: Collapse to 3 Core Services (P0)
        issue = create_issue(
            token=token,
            title="Collapse to 3 Core Services (P0)",
            labels=["P0", "MVP", "blocking", "infrastructure"],
            milestone_num=milestone_num,
            body="""## 🎯 Objective
Simplify infrastructure to exactly 3 core services for MVP: FastAPI Gateway, Next.js Frontend, Postgres+Redis.

## 🔧 Keep
- `api/` (FastAPI Gateway)
- `apps/harborhomes/` (Next.js frontend)
- Postgres + Redis (in docker-compose)

## 🗑️ Archive
- All `prepchef/services/*`
- Worker queues
- OCR services
- Neo4j adapters
- Vendor verification services

## 📋 Tasks
- [ ] Move archived services to `archive/prepchef-services/`
- [ ] Update `docker-compose.yml` to only run 3 containers
- [ ] Remove references in `Makefile`
- [ ] Update service discovery / health checks
- [ ] Update README architecture diagram

## ✅ Acceptance Criteria
- `docker-compose up` runs exactly 3 containers
- `make health` passes for all 3 services
- No broken imports or service references
- Documentation reflects new architecture

## 🔗 Related
Part of **MVP OR BUST – Dec 7 2025** milestone
Blocks: #3, #6

## 📊 Priority
**P0** - Critical path blocker"""
        )
        created_issues.append(issue)

        # Issue #3: Implement Six Real Endpoints (P0)
        issue = create_issue(
            token=token,
            title="Implement Six Real Endpoints (P0)",
            labels=["P0", "MVP", "blocking", "backend", "api"],
            milestone_num=milestone_num,
            body="""## 🎯 Objective
Build the 6 core API endpoints required for the MVP booking flow with proper error handling, security, and concurrency control.

## 🛣️ Endpoints to Implement

### 1. `POST /auth/signup`
- Create new user account
- Hash password with bcrypt
- Return JWT token

### 2. `POST /auth/login`
- Validate credentials
- Return JWT token
- Track last login timestamp

### 3. `GET /kitchens?lat,lng,from,to`
- PostGIS radius search
- Filter by availability window
- Return kitchen details + hourly rates

### 4. `POST /bookings`
- Create booking hold
- Acquire Redis lock (key: `booking:{kitchen_id}:{date}:{hour}`)
- Return booking ID + payment intent

### 5. `POST /payments/intent`
- Create Stripe PaymentIntent (test mode)
- Link to booking ID
- Return client secret

### 6. `POST /webhooks/stripe`
- Verify webhook signature
- Handle `payment_intent.succeeded`
- Mark booking as `confirmed`
- Release Redis lock

### 7. `GET /bookings/:id`
- Return booking receipt
- Include kitchen details, timestamps, payment status

## 📋 Tasks
- [ ] Implement all 7 endpoints in `api/routes/`
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
**P0** - Core MVP functionality"""
        )
        created_issues.append(issue)

        # Issue #4: Seed Realistic Kitchen Data (P1)
        issue = create_issue(
            token=token,
            title="Seed Realistic Kitchen Data (P1)",
            labels=["P1", "MVP", "database", "seed-data"],
            milestone_num=milestone_num,
            body="""## 🎯 Objective
Populate database with 5 realistic San Francisco commercial kitchen listings for MVP demo.

## 📊 Data Requirements

### Kitchens (5 listings)
- Real SF addresses (use test addresses, not real businesses)
- Hourly rates: $100–$300/hr (10000–30000 cents)
- PostGIS geometry (latitude/longitude)
- Kitchen amenities (ovens, stoves, prep space)
- Photos (placeholder URLs or local assets)

### Availability
- Next 14 days from today
- 9 AM – 9 PM daily
- Generate availability slots in `kitchen_availability` table

## 📋 Tasks
- [ ] Create Alembic migration for seed data
- [ ] Add 5 kitchen records with SF addresses
- [ ] Generate 14-day availability (9 AM–9 PM)
- [ ] Populate PostGIS `geom` column
- [ ] Add kitchen amenities/photos
- [ ] Verify data via SQL queries

## ✅ Acceptance Criteria
- `SELECT COUNT(*) FROM kitchens` returns 5
- All `geom` columns are non-null
- `GET /kitchens?lat=37.7749&lng=-122.4194` returns results
- Availability covers next 14 days
- Migration runs cleanly on fresh DB

## 🔗 Related
Part of **MVP OR BUST – Dec 7 2025** milestone
Blocks: #5, #6

## 📊 Priority
**P1** - Required for realistic demo"""
        )
        created_issues.append(issue)

        # Issue #5: Frontend Wiring / Mock Removal (P0)
        issue = create_issue(
            token=token,
            title="Frontend Wiring / Mock Removal (P0)",
            labels=["P0", "MVP", "blocking", "frontend"],
            milestone_num=milestone_num,
            body="""## 🎯 Objective
Replace all mock data with real API calls and implement complete user flow from signup to receipt.

## 🗑️ Remove
- All files in `apps/harborhomes/mockData*`
- Any hardcoded test data in components
- Mock API responses

## 🛣️ Pages to Implement

### 1. `/signup`
- Email, password, name fields
- Call `POST /auth/signup`
- Store JWT in httpOnly cookie or localStorage
- Redirect to `/search`

### 2. `/login`
- Email, password fields
- Call `POST /auth/login`
- Store JWT
- Redirect to `/search`

### 3. `/search`
- Map view (Mapbox/Leaflet)
- Date/time picker (from/to)
- Call `GET /kitchens?lat,lng,from,to`
- Display kitchen cards

### 4. `/kitchen/[id]`
- Kitchen details
- Availability calendar
- "Book Now" button → `/checkout`

### 5. `/checkout`
- Booking summary
- Stripe Elements (card input)
- Call `POST /payments/intent`
- Submit payment → Redirect to `/bookings/[id]`

### 6. `/bookings/[id]`
- Receipt page
- Booking details, payment status
- Call `GET /bookings/:id`

## 📋 Tasks
- [ ] Delete all mock data files
- [ ] Set up SWR or React Query for API calls
- [ ] Implement all 6 pages
- [ ] Add Stripe Elements for checkout
- [ ] Use test card `4242 4242 4242 4242`
- [ ] Add loading states and error handling
- [ ] Add authentication guards (redirect if not logged in)

## ✅ Acceptance Criteria
- Manual demo completes full flow locally
- No mock data remains in codebase
- `grep -r 'mockData' apps/harborhomes` returns 0 results
- Stripe test payment succeeds
- All pages render without console errors

## 🔗 Related
Part of **MVP OR BUST – Dec 7 2025** milestone
Depends on: #3, #4
Blocks: #6

## 📊 Priority
**P0** - Critical for MVP demo"""
        )
        created_issues.append(issue)

        # Issue #6: End-to-End E2E Pipeline (P0)
        issue = create_issue(
            token=token,
            title="End-to-End E2E Pipeline (P0)",
            labels=["P0", "MVP", "blocking", "testing", "e2e"],
            milestone_num=milestone_num,
            body="""## 🎯 Objective
Implement comprehensive E2E and integration tests covering the full booking flow and edge cases.

## 🧪 Playwright E2E: `tests/e2e/HappyPath.spec.ts`

### Test Flow
1. Navigate to `/signup`
2. Create account with unique email
3. Verify redirect to `/search`
4. Enter SF coordinates + next week date range
5. Click first kitchen result
6. Click "Book Now"
7. Fill Stripe test card `4242 4242 4242 4242`
8. Submit payment
9. Verify redirect to `/bookings/[id]`
10. Assert booking status = "confirmed"
11. Assert kitchen name displayed
12. Assert total price matches

## 🧪 Pytest Integration Tests

### `tests/concurrency/test_booking_race.py`
- Spawn 50 parallel requests to `POST /bookings`
- Same kitchen, same timeslot
- Assert: 1 succeeds (201), 49 fail (409 Conflict)

### `tests/webhooks/test_stripe_webhook.py`
- Mock Stripe webhook payload
- Verify signature validation
- Assert booking status updated to "confirmed"
- Assert idempotency (replay same webhook → no duplicate)

## 📋 Tasks
- [ ] Set up Playwright in `tests/e2e/`
- [ ] Write `HappyPath.spec.ts`
- [ ] Add Playwright to CI pipeline
- [ ] Write `test_booking_race.py`
- [ ] Write `test_stripe_webhook.py`
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
**P0** - Quality gate for MVP"""
        )
        created_issues.append(issue)

        # Issue #7: Security Gates and Linters (P1)
        issue = create_issue(
            token=token,
            title="Security Gates and Linters (P1)",
            labels=["P1", "MVP", "security", "ci-cd"],
            milestone_num=milestone_num,
            body="""## 🎯 Objective
Add automated security checks and linting rules to prevent common vulnerabilities and code quality issues.

## 🔒 Security Checks

### 1. Conflict Marker Detection
- Fail CI if `<<<<<<<`, `=======`, `>>>>>>>` found
- Add to `make quality-check`

### 2. Secret Scanning
- Install Gitleaks or TruffleHog
- Allowlist `.env.example`, `*.test.ts`
- Fail CI on hardcoded secrets

### 3. HTTP Timeout Validation
- Custom ruff/eslint rule
- Fail on `requests.get()` without timeout
- Fail on `fetch()` without AbortSignal

### 4. Idempotency Key Validation
- Unit tests for `POST /bookings`
- Same idempotency key → 200 (cached response)
- Different key, same data → 409 Conflict

## 📋 Tasks
- [ ] Add conflict marker check to CI
- [ ] Install Gitleaks, configure allowlist
- [ ] Create custom ruff rule for HTTP timeout
- [ ] Create custom eslint rule for fetch timeout
- [ ] Write idempotency key tests
- [ ] Update `make quality-check` to run all gates
- [ ] Document in `CONTRIBUTING.md`

## ✅ Acceptance Criteria
- CI runs `make quality-check` → all checks pass
- No false positives on allowlisted files
- Idempotency tests cover edge cases
- Documentation updated with new rules

## 🔗 Related
Part of **MVP OR BUST – Dec 7 2025** milestone

## 📊 Priority
**P1** - Prevents security regressions"""
        )
        created_issues.append(issue)

        # Issue #8: Metrics & KPIs Dashboard (P2)
        issue = create_issue(
            token=token,
            title="Metrics & KPIs Dashboard (P2)",
            labels=["P2", "MVP", "observability", "metrics"],
            milestone_num=milestone_num,
            body="""## 🎯 Objective
Set up Prometheus metrics and Grafana dashboard to monitor MVP health and performance.

## 📊 Metrics to Expose

### Application Metrics
- `e2e_test_pass_rate` (gauge, 0-100%)
- `booking_create_latency_ms` (histogram, p50/p95/p99)
- `booking_conflict_count` (counter)
- `stripe_webhook_success_rate` (gauge)
- `active_bookings_count` (gauge)

### Infrastructure Metrics
- API response time (per endpoint)
- Database connection pool usage
- Redis cache hit rate

## 📋 Tasks
- [ ] Add Prometheus exporter to FastAPI (`/metrics` endpoint)
- [ ] Instrument booking endpoints
- [ ] Set up Grafana in `docker-compose.yml`
- [ ] Create dashboard with 4 panels: E2E pass rate, booking latency, conflict count, webhook success
- [ ] Export dashboard JSON to `observability/grafana-dashboard.json`
- [ ] Add screenshot to README
- [ ] Add `make monitor` command

## ✅ Acceptance Criteria
- `make monitor` launches Grafana at localhost:3000
- Dashboard displays real-time metrics
- README includes dashboard screenshot
- Metrics survive service restarts

## 🔗 Related
Part of **MVP OR BUST – Dec 7 2025** milestone

## 📊 Priority
**P2** - Nice-to-have for MVP, critical post-launch"""
        )
        created_issues.append(issue)

        # Issue #9: Squash & Tag Release (P0)
        issue = create_issue(
            token=token,
            title="Squash & Tag Release (P0)",
            labels=["P0", "MVP", "blocking", "release"],
            milestone_num=milestone_num,
            body="""## 🎯 Objective
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
- [ ] Tag `v0.3.0-mvp-candidate`
- [ ] Update `RELEASE_NOTES.md`
- [ ] Push tag to origin
- [ ] Verify tag builds successfully in CI

## ✅ Acceptance Criteria
- Main branch history < 100 commits (or reasonable number)
- Tag `v0.3.0-mvp-candidate` exists
- Tag builds successfully in CI
- `RELEASE_NOTES.md` documents all changes
- No broken references after squash

## 🔗 Related
Part of **MVP OR BUST – Dec 7 2025** milestone
Depends on: #6

## 📊 Priority
**P0** - Final step before MVP launch

## ⚠️ Warning
This rewrites git history. Coordinate with team before executing."""
        )
        created_issues.append(issue)

        # Issue #10: Post-MVP Plan (P2)
        issue = create_issue(
            token=token,
            title="Post-MVP Plan (P2)",
            labels=["P2", "MVP", "planning", "post-launch"],
            milestone_num=milestone_num,
            body="""## 🎯 Objective
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
**P2** - Planning only, execution after MVP ships"""
        )
        created_issues.append(issue)

        print()
        print("=" * 60)
        print(f"✅ Milestone created: {MILESTONE_TITLE}")
        print(f"🚀 {len(created_issues)} issues generated and assigned")
        print(f"🧩 All issues linked to milestone #{milestone_num}")
        print(f"🕒 Target: Dec 7 2025 23:59 PT")
        print()
        print("📋 Created Issues:")
        print()
        for issue in created_issues:
            print(f"   #{issue['number']}: {issue['title']}")
            print(f"   → {issue['html_url']}")
            print()
        print("Next steps:")
        print(f"1. Review issues at: https://github.com/{REPO_OWNER}/{REPO_NAME}/milestone/{milestone_num}")
        print("2. Prioritize P0 issues first")
        print("3. Start with Issue #1 (README cleanup)")
        print()
        print("🎯 No excuses. Just ship.")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
