# Golden Path Demo

## Purpose

This document defines the "Golden Path" - the ideal end-to-end user journey through the Prep platform, from vendor onboarding to compliant booking completion.

**Use Cases:**
- Demo for investors and stakeholders
- Integration test scenario
- Developer onboarding walkthrough
- Regression testing suite

---

## The Golden Path Journey

### Persona: Maria, Short-Term Rental Operator

Maria owns 3 properties in San Francisco and wants to ensure compliance with city regulations.

---

## Phase 1: Vendor Onboarding (15 minutes)

### Step 1: Create Account

```bash
# Using prepctl CLI
prepctl vendor:onboard \
  --business-name "Bay Area Stays LLC" \
  --email "maria@bayareastays.com" \
  --city "San Francisco"
```

**Expected Outcome:**
- ✅ Vendor account created with `vendor_id`
- ✅ Stripe Connect account created
- ✅ Email verification sent
- ✅ Status: `pending_verification`

**Audit Trail:**
- Audit log entry: `CREATE vendor` by `system`

---

### Step 2: Add First Property

```bash
prepctl facility:create \
  --vendor-id "vendor-123" \
  --address "1234 Valencia St, San Francisco, CA 94110" \
  --property-type "entire_home" \
  --bedrooms 2 \
  --bathrooms 1.5 \
  --max-occupancy 4
```

**Expected Outcome:**
- ✅ Property created with `facility_id`
- ✅ Jurisdiction auto-detected: `US-CA-SF`
- ✅ Zoning data fetched
- ✅ Status: `draft`

**Audit Trail:**
- Audit log entry: `CREATE facility` by `maria@bayareastays.com`

---

## Phase 2: Compliance Check (5 minutes)

### Step 3: Run Initial Compliance Check

```bash
prepctl compliance:check \
  --facility-id "facility-456" \
  --jurisdiction "San Francisco"
```

**Expected Outcome:**
- ✅ Compliance check executed via RegEngine
- ⚠️ Status: `non_compliant`
- 📋 Blocking issues identified:
  1. Missing Business Registration Certificate
  2. Missing TOB (Transient Occupancy Registration)
  3. Fire safety inspection required
  4. Owner-occupancy declaration needed

**RegEngine Output:**
```json
{
  "overall_status": "non_compliant",
  "compliance_score": 35,
  "checks": [
    {
      "rule_id": "SF-BRC-001",
      "rule_name": "Business Registration Certificate Required",
      "passed": false,
      "severity": "blocking",
      "resolution": "Apply at https://businessportal.sfgov.org"
    },
    {
      "rule_id": "SF-TOB-001",
      "rule_name": "Transient Occupancy Registration",
      "passed": false,
      "severity": "blocking",
      "resolution": "Register at SF Treasurer portal"
    },
    {
      "rule_id": "SF-FIRE-001",
      "rule_name": "Fire Safety Inspection",
      "passed": false,
      "severity": "blocking",
      "resolution": "Schedule inspection with SFFD"
    }
  ]
}
```

**Audit Trail:**
- Audit log entry: `COMPLIANCE_CHECK facility` by `maria@bayareastays.com`

---

## Phase 3: Permit Acquisition (Mock Mode)

### Step 4: Apply for Permits (Using Mock Portals)

```bash
# Start mock government portals
docker compose -f docker-compose.mock.yml up -d

# Apply for SF STR registration (mock)
curl -X POST http://localhost:8003/api/v1/str/register \
  -H "Content-Type: application/json" \
  -d '{
    "property_address": "1234 Valencia St, San Francisco, CA 94110",
    "owner_name": "Maria Rodriguez",
    "contact_email": "maria@bayareastays.com",
    "property_type": "entire_home"
  }'
```

**Mock Response:**
```json
{
  "registration_number": "SF-STR-2025-ABC123",
  "status": "submitted",
  "message": "Registration submitted.",
  "next_steps": [
    "Obtain Business Registration Certificate",
    "Complete Transient Occupancy Registration",
    "Schedule fire safety inspection"
  ]
}
```

### Step 5: Upload Permit Documents

```bash
prepctl facility:upload-permit \
  --facility-id "facility-456" \
  --permit-type "str_permit" \
  --permit-number "SF-STR-2025-ABC123" \
  --document "/path/to/permit.pdf"
```

**Expected Outcome:**
- ✅ Document uploaded to MinIO/S3
- ✅ Permit record created in database
- ✅ Expiration tracking enabled
- ✅ Permit status: `active`

---

### Step 6: Re-run Compliance Check

```bash
prepctl compliance:check \
  --facility-id "facility-456" \
  --jurisdiction "San Francisco"
```

**Expected Outcome:**
- ✅ Status: `compliant`
- ✅ Compliance score: 100
- ✅ All blocking issues resolved
- ✅ Facility status updated to `active`

**Audit Trail:**
- Audit log entry: `APPROVE facility` by `regengine`

---

## Phase 4: First Booking (Real-Time)

### Step 7: Create Booking Request

```bash
prepctl booking:create \
  --facility-id "facility-456" \
  --check-in "2025-12-01" \
  --check-out "2025-12-03" \
  --guest-count 2 \
  --guest-email "guest@example.com"
```

**Expected Outcome:**
- ✅ Booking created with `booking_id`
- ✅ Pricing calculated:
  - Base rent: $600 (2 nights × $300)
  - Cleaning fee: $100
  - Platform fee (4%): $28
  - SF TOT (14%): $98
  - **Total: $826**
- ✅ Compliance check passed (re-validated)
- ✅ Status: `pending_payment`

**Audit Trail:**
- Audit log entry: `CREATE booking` by `guest@example.com`

---

### Step 8: Process Payment (Mock Stripe)

```bash
# Create payment intent (mock Stripe)
curl -X POST http://localhost:8001/v1/payment_intents \
  -H "Authorization: Bearer sk_test_mock" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 82600,
    "currency": "usd",
    "application_fee_amount": 2800,
    "transfer_data": {
      "destination": "acct_vendor123"
    },
    "metadata": {
      "booking_id": "booking-789"
    }
  }'

# Confirm payment intent (simulate successful payment)
curl -X POST http://localhost:8001/v1/payment_intents/{intent_id}/confirm \
  -H "Authorization: Bearer sk_test_mock"
```

**Expected Outcome:**
- ✅ Payment intent status: `succeeded`
- ✅ Funds captured: $826
- ✅ Platform fee: $28
- ✅ Host payout scheduled: $698
- ✅ Tax liability recorded: $98
- ✅ Booking status: `confirmed`

**Ledger Entries Created:**
```
1. Debit  Cash           $826  (guest payment)
2. Credit Revenue        $700  (rental income)
3. Credit Platform Fee   $28   (platform revenue)
4. Credit Tax Liability  $98   (TOT collected)
5. Debit  Host Payable   $698  (owed to Maria)
```

**Audit Trail:**
- Audit log entry: `PAYMENT booking` by `payment_service`
- Multiple ledger entries created (immutable)

---

### Step 9: Send Confirmation

```bash
# Notification sent automatically via webhook
# (MailHog captures email in local dev)

# View email in MailHog UI
open http://localhost:8026
```

**Expected Outcome:**
- ✅ Confirmation email sent to guest
- ✅ Booking details email sent to Maria
- ✅ Receipt generated with fee breakdown

---

## Phase 5: Monitoring & Reporting

### Step 10: View Dashboard

```bash
# Open Grafana dashboards
prepctl grafana
```

**Metrics to Verify:**
- ✅ Bookings created: 1
- ✅ Revenue today: $28 (platform fee)
- ✅ Payment success rate: 100%
- ✅ Compliance checks passed: 100%
- ✅ API latency P95: < 500ms

---

### Step 11: Export Compliance Report

```bash
prepctl audit:export \
  --start-date "2025-01-01" \
  --end-date "2025-12-31" \
  --format pdf \
  --output compliance-report-2025.pdf
```

**Expected Outcome:**
- ✅ PDF generated with:
  - All vendor activities
  - Permit history
  - Booking history
  - Compliance check results
  - Payment transactions
- ✅ Ready for auditor review

---

## Phase 6: Ongoing Operations

### Step 12: Permit Renewal Reminder

```bash
# (Automated - runs daily)
prepctl permits:check-expiring --days 30
```

**Expected Outcome:**
- 🔔 Alert: "SF-STR-2025-ABC123 expires in 28 days"
- 📧 Email sent to Maria with renewal instructions

---

### Step 13: Tax Remittance

```bash
# (Automated - runs monthly)
prepctl tax:remit \
  --jurisdiction "San Francisco" \
  --period "2025-12"
```

**Expected Outcome:**
- ✅ TOT remittance report generated
- ✅ Total collected: $98
- ✅ Payment instructions for SF Treasurer

---

## Success Criteria

The Golden Path is successful when:

- ✅ Vendor onboarding: < 15 minutes
- ✅ Compliance check: < 5 seconds
- ✅ Booking creation: < 2 seconds
- ✅ Payment processing: < 3 seconds
- ✅ Zero manual intervention required
- ✅ All audit logs created
- ✅ All compliance reports exportable

---

## Automated Golden Path Test

```bash
# Run full Golden Path as automated test
prepctl test:golden-path --verbose

# Expected output:
# ✓ Phase 1: Vendor Onboarding [PASS]
# ✓ Phase 2: Compliance Check [PASS]
# ✓ Phase 3: Permit Acquisition [PASS]
# ✓ Phase 4: First Booking [PASS]
# ✓ Phase 5: Payment Processing [PASS]
# ✓ Phase 6: Reporting [PASS]
#
# Golden Path: PASS (23.4s)
```

---

## Troubleshooting

### Common Issues

**Compliance check fails unexpectedly:**
```bash
# Check RegEngine logs
docker compose logs python-compliance --tail 50

# Verify jurisdiction data
prepctl jurisdiction:info --code "US-CA-SF"
```

**Payment processing fails:**
```bash
# Check mock Stripe is running
curl http://localhost:8001/

# View recent payment intents
curl http://localhost:8001/debug/payment_intents
```

**Permit upload fails:**
```bash
# Check MinIO is running
curl http://localhost:9001/

# Test upload directly
prepctl storage:test-upload
```

---

## Demo Script for Stakeholders

**Duration: 10 minutes**

**Script:**

> "Let me show you how Prep turns compliance from a blocker into a competitive advantage."
>
> [Phase 1] "Maria owns 3 properties in San Francisco. She signs up in 2 clicks. Prep immediately creates her Stripe Connect account for payouts."
>
> [Phase 2] "She adds her first property. Watch this - Prep instantly runs a compliance check against 47 SF regulations. In 3 seconds, we tell her exactly what permits she needs."
>
> [Phase 3] "She uploads her STR permit. Prep auto-extracts the expiration date and sets a renewal reminder for 30 days before it expires."
>
> [Phase 4] "A guest books her property. Prep rechecks compliance in real-time - still good. Payment is processed via Stripe Connect. Platform fee, tax, and host payout are automatically calculated and split."
>
> [Phase 5] "Look at our dashboard - every metric is green. P95 latency under 500ms. Payment success rate 99.9%. Compliance accuracy 100%."
>
> [Phase 6] "At any time, Maria can export a PDF compliance report for auditors, investors, or city inspectors. Everything is documented, immutable, and audit-ready."
>
> **"That's the Prep Golden Path. Compliance in seconds, not weeks."**

---

## Document Metadata

- **Version**: 1.0
- **Last Updated**: 2025-11-13
- **Owner**: Product + Engineering
- **Review Cycle**: After each major release

---

## Related Documents

- [Product Spine](./PRODUCT_SPINE.md)
- [Architecture Overview](./architecture.md)
- [prepctl CLI Reference](./PREPCTL_REFERENCE.md)
