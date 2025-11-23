# MVP Bootstrap Guide

This directory contains scripts to automatically create the **"MVP OR BUST – Dec 7 2025"** milestone and 10 linked GitHub issues for the Prep repository.

## 🎯 What This Does

Creates a complete YC-style MVP sprint structure:

- **1 Milestone**: "MVP OR BUST – Dec 7 2025" (due Dec 7, 2025 23:59 PT)
- **10 Issues**: Labeled, prioritized, and linked to the milestone
  - 6 × P0 (blocking) issues
  - 2 × P1 issues
  - 2 × P2 (post-MVP) issues

**Goal**: A non-founder can complete a real $100+ booking in Stripe test mode, end-to-end, with zero manual intervention.

## 🚀 Quick Start

### Prerequisites

1. **GitHub Personal Access Token** with `repo` scope
   - Create at: https://github.com/settings/tokens/new
   - Required permissions: `repo` (full control of private repositories)
   - Copy the token (you'll only see it once)

### Option 1: Python Script (Recommended)

```bash
# From the repository root
cd /home/user/Prep

# Run with token as argument
python3 scripts/bootstrap_mvp.py YOUR_GITHUB_TOKEN_HERE

# OR set as environment variable
export GITHUB_TOKEN=your_github_token_here
python3 scripts/bootstrap_mvp.py
```

### Option 2: Bash Script (requires GitHub CLI)

```bash
# Install GitHub CLI first (if not installed)
# https://cli.github.com/manual/installation

# Authenticate
gh auth login

# Run the script
./scripts/bootstrap-mvp.sh
```

## 📋 What Gets Created

### Milestone
- **Title**: MVP OR BUST – Dec 7 2025
- **Due Date**: December 7, 2025, 11:59 PM PT
- **Description**: Complete definition of done with success metrics

### Issues

#### P0 (Blocking) - Must Ship for MVP
1. **README and Repo Hygiene** - Clean up conflicts, add badges, archive legacy docs
2. **Collapse to 3 Core Services** - Simplify to FastAPI + Next.js + Postgres/Redis only
3. **Implement Six Real Endpoints** - Auth, search, booking, payment, webhook, receipt
4. **Frontend Wiring / Mock Removal** - Wire real API calls, remove all mocks
5. **End-to-End E2E Pipeline** - Playwright + pytest full flow tests
6. **Squash & Tag Release** - Clean history, tag v0.3.0-mvp-candidate

#### P1 (Next 2 Days After MVP)
7. **Seed Realistic Kitchen Data** - 5 SF kitchens with real addresses and availability
8. **Security Gates and Linters** - Conflict detection, secret scanning, HTTP timeouts

#### P2 (Post-MVP Follow-up)
9. **Metrics & KPIs Dashboard** - Prometheus + Grafana observability
10. **Post-MVP Plan** - Onboarding, dogfooding, compliance queue

## 🔍 Verification

After running the script, verify:

```bash
# Check milestone was created
gh milestone list --repo PetrefiedThunder/Prep

# Check issues were created
gh issue list --repo PetrefiedThunder/Prep --milestone "MVP OR BUST – Dec 7 2025"

# Or visit in browser
open "https://github.com/PetrefiedThunder/Prep/milestones"
```

## 🛠️ Troubleshooting

### "GitHub token required"
- Make sure you created a token with `repo` scope
- Pass it as argument or set `GITHUB_TOKEN` environment variable

### "Milestone might already exist"
- The script will find and use the existing milestone
- Safe to re-run

### "gh: command not found"
- Use the Python script instead (Option 1)
- Or install GitHub CLI: https://cli.github.com/

### API Rate Limit
- GitHub API allows 5,000 requests/hour for authenticated requests
- Creating 1 milestone + 10 issues = 11 requests (well within limit)

## 📊 Expected Output

```
🚀 Bootstrapping MVP Milestone for PetrefiedThunder/Prep
============================================================

📍 Creating milestone: MVP OR BUST – Dec 7 2025
✅ Milestone #X created

📝 Creating: README and Repo Hygiene (P0)
   ✅ Issue #XXX: https://github.com/PetrefiedThunder/Prep/issues/XXX

📝 Creating: Collapse to 3 Core Services (P0)
   ✅ Issue #XXX: https://github.com/PetrefiedThunder/Prep/issues/XXX

... (8 more issues)

============================================================
✅ Milestone created: MVP OR BUST – Dec 7 2025
🚀 10 issues generated and assigned
🧩 All issues linked to milestone #X
🕒 Target: Dec 7 2025 23:59 PT

📋 Created Issues:

   #XXX: README and Repo Hygiene (P0)
   → https://github.com/PetrefiedThunder/Prep/issues/XXX

   ... (9 more)

Next steps:
1. Review issues at: https://github.com/PetrefiedThunder/Prep/milestone/X
2. Prioritize P0 issues first
3. Start with Issue #1 (README cleanup)

🎯 No excuses. Just ship.
============================================================
```

## 🎓 Understanding the Issue Structure

Each issue includes:

- **🎯 Objective**: Clear goal statement
- **📋 Tasks**: Detailed checklist of work items
- **✅ Acceptance Criteria**: Definition of done
- **🔗 Related**: Dependencies and blockers
- **📊 Priority**: P0/P1/P2 classification

### Dependencies Flow

```
Issue #1 (README) ──┐
                    ├──> Issue #3 (Endpoints) ──> Issue #5 (Frontend) ──> Issue #6 (E2E) ──> Issue #9 (Release)
Issue #2 (Services)─┘                                    ↑
                                                          │
                                    Issue #4 (Seed Data)──┘
```

Start with #1 and #2, then #3, then #4 and #5 in parallel, then #6, finally #9.

## 🔄 Re-running the Script

The script is **idempotent-safe**:
- If milestone exists, it will find and reuse it
- If you want fresh issues, manually delete the old ones first
- Or change the milestone title in the script

## 📞 Support

- **Script Issues**: Check `scripts/bootstrap_mvp.py` line numbers in error messages
- **GitHub API Issues**: Check https://www.githubstatus.com/
- **Token Issues**: Verify scopes at https://github.com/settings/tokens

## 🎯 Definition of Done (MVP)

The milestone is complete when:

✅ Signup → Search → Book → Pay → Receipt runs in Playwright CI
✅ No merge conflicts, no mocks, no manual steps
✅ Three services only (FastAPI + Next.js + Postgres/Redis)
✅ Test coverage ≥ 55% and E2E pass rate ≥ 95%

**Target**: December 7, 2025, 11:59 PM PT

---

**Version**: 1.0
**Created**: 2025-11-23
**Maintainer**: @PetrefiedThunder
**Repository**: https://github.com/PetrefiedThunder/Prep
