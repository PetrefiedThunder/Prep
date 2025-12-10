# MVP 85% Vertical Slice - E2E Test Plan

This document outlines the end-to-end test plan for the compliance workflow feature.

## Prerequisites

1. **Database Migration Applied**: Run `supabase/migration_mvp_compliance.sql` in Supabase SQL editor
2. **Storage Bucket Created**: Create `kitchen-documents` bucket in Supabase Storage with public access
3. **Admin User Created**: Manually create an admin user in the database:
   ```sql
   UPDATE public.profiles
   SET role = 'admin'
   WHERE email = 'admin@test.com';
   ```

## Test Scenario: Happy Path Vertical Slice

### 1. Owner Registration and Kitchen Creation

**Steps:**
1. Navigate to `/auth/signup`
2. Select "List my kitchen" from role dropdown
3. Enter email: `owner@test.com`
4. Enter password: `testpass123`
5. Click "Sign Up"
6. Verify email confirmation
7. Log in at `/auth/login`
8. Navigate to `/owner/kitchens/new`
9. Create kitchen with:
   - Title: "Test Commercial Kitchen"
   - Address: "123 Main St"
   - City: "San Francisco"
   - State: "CA"
   - ZIP: "94105"
   - Price: $50/hour
   - Capacity: 5 people
10. Submit form

**Expected Results:**
- Kitchen created successfully
- Redirected to `/owner/kitchens`
- Kitchen shows in owner dashboard
- Kitchen has `compliance_approved = false`
- Kitchen is NOT visible in public search

### 2. Document Upload

**Steps:**
1. From owner dashboard, click on kitchen
2. Navigate to "Compliance" tab (or `/owner/kitchens/[id]/compliance`)
3. Upload Health Permit:
   - Click "Choose file" under Health Permit section
   - Select PDF or image file
   - Click "Upload Document"
4. Upload Insurance Certificate:
   - Click "Choose file" under Insurance section
   - Select PDF or image file
   - Click "Upload Document"

**Expected Results:**
- Both documents show "⏳ Pending Review" status
- Documents are visible in owner view
- Kitchen still shows as non-compliant
- Compliance banner shows: "⚠️ Upload and get approval for both documents..."

### 3. Admin Review - Approval

**Steps:**
1. Log out from owner account
2. Navigate to `/auth/login`
3. Log in as admin: `admin@test.com`
4. Navigate to `/admin/compliance`
5. Verify 2 pending documents are visible
6. For Health Permit document:
   - Click "View Document →" to review file
   - Add review note: "Valid until 2026"
   - Click "✓ Approve"
7. For Insurance Certificate:
   - Click "View Document →" to review file
   - Add review note: "Coverage adequate"
   - Click "✓ Approve"

**Expected Results:**
- Both documents disappear from pending queue
- Admin dashboard shows "✓ No pending documents to review"
- Database trigger automatically updates kitchen `compliance_approved = true`

### 4. Kitchen Becomes Bookable

**Steps:**
1. Log out from admin account
2. Log in as owner: `owner@test.com`
3. Navigate to `/owner/kitchens/[id]/compliance`
4. Verify compliance status
5. Log out
6. Register as tenant: `tenant@test.com`, role: "Rent a kitchen"
7. Navigate to `/kitchens`
8. Search for kitchens in San Francisco

**Expected Results:**
- Owner sees: "✅ Your kitchen is compliant and available for booking"
- Both documents show "✓ Approved" status with review notes
- Tenant can see "Test Commercial Kitchen" in search results
- Kitchen is bookable

### 5. Tenant Booking with Payment

**Steps:**
1. As tenant, click on "Test Commercial Kitchen"
2. Select booking date and time
3. Choose duration: 4 hours
4. Click "Book Now"
5. Complete Stripe test checkout:
   - Card: 4242 4242 4242 4242
   - Expiry: Any future date
   - CVC: Any 3 digits
6. Complete payment

**Expected Results:**
- Total cost calculated: $200 (4 hours × $50/hour)
- Stripe checkout session created
- Payment processed successfully
- Booking created with status: "confirmed"
- Tenant redirected to `/bookings/success`
- Booking appears in tenant dashboard at `/renter/bookings`
- Booking appears in owner dashboard at `/owner/bookings`

## Edge Case Tests

### Test: Document Rejection Flow

**Steps:**
1. Upload a document as owner
2. Admin reviews and clicks "✗ Reject"
3. Add note: "Document expired, please upload current version"
4. Owner views compliance page

**Expected:**
- Document shows "✗ Rejected" status
- Review note is visible
- Upload form reappears for rejected document
- Kitchen remains non-compliant
- Kitchen not visible in search

### Test: Booking Conflict Prevention

**Steps:**
1. Create booking for kitchen from 10:00-12:00
2. Attempt to book same kitchen from 11:00-13:00

**Expected:**
- Second booking rejected with conflict error
- Only first booking confirmed

### Test: Unauthorized Access

**Steps:**
1. Tenant user tries to access `/admin/compliance`
2. Owner tries to review documents (POST to review endpoint)
3. User tries to upload document for kitchen they don't own

**Expected:**
- All unauthorized actions redirected or show error
- RLS policies prevent data access

## Database Validation Queries

Run these queries to verify correct data state:

```sql
-- Check owner has correct role
SELECT email, role FROM public.profiles WHERE email = 'owner@test.com';
-- Expected: role = 'owner'

-- Check kitchen compliance status
SELECT title, compliance_approved FROM public.kitchens WHERE title = 'Test Commercial Kitchen';
-- Expected: compliance_approved = true (after approval)

-- Check documents are approved
SELECT document_type, status, reviewer_id FROM public.kitchen_documents
WHERE kitchen_id = '[kitchen-id]';
-- Expected: Both documents status = 'approved', reviewer_id is not null

-- Check booking was created
SELECT status, total_amount, total_hours FROM public.bookings
WHERE kitchen_id = '[kitchen-id]';
-- Expected: status = 'confirmed', total_amount = 200.00, total_hours = 4.00
```

## Success Criteria

- ✅ Owner can register with 'owner' role
- ✅ Owner can create kitchen
- ✅ Owner can upload 2 compliance documents
- ✅ Admin can view pending documents
- ✅ Admin can approve/reject documents
- ✅ Kitchen becomes bookable after both documents approved
- ✅ Non-compliant kitchens hidden from public search
- ✅ Tenant can book approved kitchen
- ✅ Payment integration works correctly
- ✅ Booking conflict prevention works
- ✅ All RLS policies enforce proper access control

## Manual Test Checklist

- [ ] Database migration applied successfully
- [ ] Storage bucket created and accessible
- [ ] Owner registration with role selection works
- [ ] Kitchen creation works
- [ ] Document upload UI renders correctly
- [ ] File upload to Supabase Storage succeeds
- [ ] Admin dashboard shows pending documents
- [ ] Document approval updates status correctly
- [ ] Kitchen compliance_approved flag auto-updates
- [ ] Compliant kitchens appear in search
- [ ] Non-compliant kitchens hidden from search
- [ ] Tenant booking flow works end-to-end
- [ ] Stripe payment integration works
- [ ] Document rejection flow works
- [ ] Review notes display correctly
- [ ] Unauthorized access is prevented
- [ ] All edge cases tested

## Notes

- For production, add automated Playwright or Cypress tests
- Consider adding webhook tests for Supabase triggers
- Add load testing for concurrent document uploads
- Test with various file formats (PDF, JPG, PNG)
- Test file size limits and validation
