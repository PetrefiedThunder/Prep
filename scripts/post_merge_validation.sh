#!/usr/bin/env bash
# Usage: ./post_merge_validation.sh <owner/repo>
# Example: ./post_merge_validation.sh PetrefiedThunder/Prep
#
# Creates GitHub issues that track post-merge operational validation workstreams.
# Requires the GitHub CLI (gh) to be authenticated with sufficient repo scope.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <owner/repo>" >&2
  exit 1
fi

REPO="$1"

read -r -d '' BODY_FUNCTIONAL <<'EOM'
**Goal:** Confirm end-to-end behavior.

**Checklist**
- [ ] All tests green (`pytest` or equivalent)
- [ ] Manually verify `/healthz`, `/bookings`, `/compliance/evaluate`, `/payments/webhook`
- [ ] Simulate booking with $10 Stripe sandbox; payout completes
- [ ] Compliance evaluator blocks unpermitted maker (DENY case)
EOM

read -r -d '' BODY_INFRA <<'EOM'
**Goal:** Boot staging like prod.

**Checklist**
- [ ] `docker-compose up` or `helm install prep-staging` succeeds
- [ ] Grafana shows webhook latency + booking count
- [ ] Log aggregation and Slack alerting online
EOM

read -r -d '' BODY_DATA <<'EOM'
**Goal:** Compliance data is fresh and correct.

**Checklist**
- [ ] Nightly cron populates `regulation_manifest`
- [ ] SF / JT / LA parsed correctly
- [ ] Spot-check against official sources
EOM

read -r -d '' BODY_PAYMENTS <<'EOM'
**Goal:** Money moves correctly.

**Checklist**
- [ ] Stripe sandbox capture + refund flows work
- [ ] DB ledger reconciles deposits/payouts
- [ ] Webhook idempotency validated (10× replay → 1 record)
EOM

read -r -d '' BODY_COMPLIANCE <<'EOM'
**Goal:** Legal readiness.

**Checklist**
- [ ] COI upload parses expiry/limits
- [ ] Day-pass insurance returns policy_id
- [ ] Admin shows compliance diffs + audit logs
EOM

read -r -d '' BODY_RBAC <<'EOM'
**Goal:** Safe operations.

**Checklist**
- [ ] Admin approves host, refunds booking, views audit log
- [ ] Ops role scoped to support actions
- [ ] Unauthorized access returns 403
EOM

read -r -d '' BODY_PILOT <<'EOM'
**Goal:** Business rehearsal.

**Checklist**
- [ ] Seed 3 hosts / 10 makers
- [ ] Run 2 real bookings and record metrics
- [ ] Collect feedback from both sides
- [ ] Update RUNBOOK.md with lessons
EOM

read -r -d '' BODY_PACKET <<'EOM'
**Goal:** Proof for diligence.

**Deliverables**
- [ ] Screenshots: booking → payout → compliance gate
- [ ] Grafana: uptime + ETL visuals
- [ ] 90–120s video walkthrough
- [ ] Compliance memo for CA + federal layers
EOM

create_issue() {
  local title="$1"
  local body="$2"
  shift 2
  gh issue create -R "$REPO" -t "$title" -b "$body" "$@"
}

create_issue "🧪 Functional Verification"       "$BODY_FUNCTIONAL" --label qa --label priority-high
create_issue "⚙️ Infrastructure Smoke Test"      "$BODY_INFRA"       --label infra --label observability
create_issue "🧩 Data & ETL Sanity"              "$BODY_DATA"        --label etl --label compliance
create_issue "💸 Payments & Accounting Audit"   "$BODY_PAYMENTS"    --label payments --label finance --label security
create_issue "🛡️ Compliance & Insurance Validation" "$BODY_COMPLIANCE" --label compliance --label insurance
create_issue "🧑‍💼 Admin & RBAC Controls"        "$BODY_RBAC"        --label admin --label security
create_issue "🌵 Pilot Readiness — Joshua Tree + SF" "$BODY_PILOT" --label pilot --label qa
create_issue "📦 Investor & Regulator Packet"    "$BODY_PACKET"      --label docs --label investor --label priority-medium

cat <<'SUMMARY'
Created GitHub issues:
  • 🧪 Functional Verification
  • ⚙️ Infrastructure Smoke Test
  • 🧩 Data & ETL Sanity
  • 💸 Payments & Accounting Audit
  • 🛡️ Compliance & Insurance Validation
  • 🧑‍💼 Admin & RBAC Controls
  • 🌵 Pilot Readiness — Joshua Tree + SF
  • 📦 Investor & Regulator Packet
SUMMARY
