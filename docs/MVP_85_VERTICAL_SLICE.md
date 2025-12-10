# PrepChef – MVP 85% Vertical Slice

## Goal
Single happy path for a pilot customer demonstrating the complete compliance and booking workflow.

## End-to-End Flow

### 1. Owner Journey
1. OWNER registers with role selection and logs in
2. Owner creates a Kitchen (name, address, hourly pricing)
3. Owner uploads 2 compliance documents:
   - Health permit
   - Insurance certificate
4. Documents enter "pending" status awaiting admin review

### 2. Admin Journey
1. ADMIN logs in to admin dashboard
2. Admin views queue of pending compliance documents
3. Admin reviews each document and either:
   - **Approves** → Kitchen becomes bookable
   - **Rejects** → Owner must re-upload

### 3. Tenant Journey
1. TENANT registers and logs in
2. Tenant browses approved kitchens
3. Tenant selects kitchen, chooses date/time, and books slot
4. System performs:
   - ✅ Booking conflict check (no overlapping times)
   - ✅ Cost calculation (hourly_rate × duration)
   - ✅ Stripe checkout with test payment
   - ✅ Creates booking record linked to payment
   - ✅ Marks booking as CONFIRMED after successful payment

## Technical Implementation

### Database Changes (Supabase)
- Add `role` enum column to profiles table (owner, tenant, admin)
- Create `kitchen_documents` table with fields:
  - kitchen_id (FK to kitchens)
  - document_type (health_permit, insurance_certificate)
  - file_url (stored in Supabase Storage)
  - status (pending, approved, rejected)
  - uploaded_at, reviewed_at, reviewer_id
- Add RLS policies for role-based access

### Backend (Next.js Server Actions)
- `uploadKitchenDocument()` - Owner uploads compliance docs
- `reviewDocument()` - Admin approves/rejects documents
- `getDocumentsForReview()` - Fetch pending docs for admin dashboard
- Extend booking logic with conflict checking

### Frontend (Next.js Pages)
- `/auth/register` - Add role selection dropdown
- `/owner/kitchens/[id]/documents` - Document upload interface
- `/admin/compliance` - Admin review dashboard with approve/reject actions
- Extend booking flow to check kitchen compliance status

## Out of Scope
- Advanced regulatory graph (Neo4j)
- ETL/regulatory ingestion pipelines
- Multi-tenant organizations
- Non-Stripe payment rails
- Complex pricing logic (discounts, surge pricing)
- Calendar availability management

## Success Criteria
- ✅ Owner can create kitchen and upload 2 documents
- ✅ Admin can review and approve/reject documents
- ✅ Tenant can book approved kitchen with payment
- ✅ Booking conflict prevention works correctly
- ✅ E2E test passes for happy path

## Architecture Fit
This implementation extends the existing Supabase + Next.js architecture without introducing new infrastructure dependencies. All features use the current tech stack:
- **Database:** Supabase PostgreSQL with RLS
- **Auth:** Supabase Auth with role extensions
- **Storage:** Supabase Storage for document uploads
- **Payments:** Existing Stripe Connect integration
- **Frontend:** Next.js 14 App Router with server actions
