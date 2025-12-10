# MVP 85% Vertical Slice - Implementation Guide

This document describes the compliance workflow implementation for the PrepChef MVP.

## Overview

The MVP 85% vertical slice adds role-based authentication and a compliance document review workflow to ensure kitchen owners upload required documents before their kitchens become bookable.

## Architecture Alignment

**Implementation matches existing stack:**
- ✅ Supabase PostgreSQL (extended schema)
- ✅ Supabase Auth (added user roles)
- ✅ Supabase Storage (document uploads)
- ✅ Next.js 14 App Router (new pages)
- ✅ Server Actions (document management)
- ✅ Stripe Connect (existing integration)

**No new infrastructure dependencies added.**

## Features Implemented

### 1. User Roles (`user_role` enum)
- **owner**: Can list kitchens and upload compliance documents
- **tenant**: Can search and book kitchens
- **admin**: Can review and approve/reject compliance documents

### 2. Booking Conflict Detection (CRITICAL)
- **Prevents double-booking**: Checks for overlapping time slots before payment
- **Overlap algorithm**: `(RequestStart < ExistingEnd) AND (RequestEnd > ExistingStart)`
- **Statuses checked**: Both 'pending' and 'confirmed' bookings
- **User-friendly errors**: Clear messaging when slot is unavailable
- **Performance**: Uses indexed queries with count-only check

### 3. Compliance Document System
- **Document Types**: Health permit, insurance certificate
- **Document Status**: Pending, approved, rejected
- **File Storage**: Supabase Storage bucket `kitchen-documents`
- **Auto-compliance**: Kitchen `compliance_approved` flag auto-updates via trigger

### 3. Kitchen Visibility Rules
- **Non-compliant kitchens**: Hidden from public search
- **Compliant kitchens**: Visible and bookable (both documents approved)
- **Owner view**: Always see own kitchens regardless of compliance

### 4. Admin Review Workflow
- Pending documents queue at `/admin/compliance`
- Review with approval/rejection and notes
- Real-time updates via revalidation

## Files Added/Modified

### Database Schema
- `supabase/migration_mvp_compliance.sql` - Migration script

### Backend (Server Actions)
- `lib/actions/documents.ts` - Document CRUD operations
- `lib/actions/bookings.ts` - **Updated with conflict detection**
- `lib/types.ts` - TypeScript types for roles and documents

### Frontend (Pages)
- `app/auth/signup/page.tsx` - Added role selection
- `app/owner/kitchens/[id]/compliance/page.tsx` - Document upload page
- `app/owner/kitchens/[id]/compliance/DocumentUploadForm.tsx` - Upload component
- `app/owner/kitchens/[id]/compliance/DocumentStatusBadge.tsx` - Status indicator
- `app/admin/compliance/page.tsx` - Admin review dashboard
- `app/admin/compliance/ReviewDocumentForm.tsx` - Review component
- `app/owner/kitchens/KitchenCard.tsx` - Added compliance warning & button

### Documentation
- `docs/MVP_85_VERTICAL_SLICE.md` - Requirements specification
- `docs/MVP_IMPLEMENTATION_GUIDE.md` - This file
- `tests/MVP_COMPLIANCE_E2E_TEST_PLAN.md` - Test scenarios

## Setup Instructions

### 1. Apply Database Migration

Run in Supabase SQL Editor:

```sql
-- Copy and paste contents of supabase/migration_mvp_compliance.sql
```

This will:
- Add `role` column to profiles
- Create `kitchen_documents` table
- Add `compliance_approved` column to kitchens
- Create RLS policies for role-based access
- Add trigger to auto-update compliance status
- Update `handle_new_user()` function to set role from metadata

### 2. Create Storage Bucket

In Supabase Dashboard:
1. Go to Storage
2. Create new bucket: `kitchen-documents`
3. Set to **Public** access
4. Configure RLS policies:

```sql
-- Allow owners to upload to their kitchen folders
CREATE POLICY "Owners can upload kitchen documents"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'kitchen-documents' AND
  (storage.foldername(name))[1] IN (
    SELECT id::text FROM public.kitchens WHERE owner_id = auth.uid()
  )
);

-- Anyone can view documents (for admin review)
CREATE POLICY "Authenticated users can view documents"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'kitchen-documents');
```

### 3. Create Admin User

Manually promote a user to admin:

```sql
-- After user signs up normally
UPDATE public.profiles
SET role = 'admin'
WHERE email = 'admin@yourdomain.com';
```

### 4. Test the Flow

Follow the E2E test plan in `tests/MVP_COMPLIANCE_E2E_TEST_PLAN.md`

## API Endpoints (Server Actions)

### Booking Management

```typescript
// Create checkout session with conflict detection
createCheckoutSession(kitchenId: string, startTime: string, endTime: string)
// Returns: { url: string } | { error: string }
// Checks for conflicts BEFORE creating Stripe session

// Get user's bookings (tenant view)
getUserBookings()

// Get owner's bookings (owner view)
getOwnerBookings()
```

**Conflict Detection Logic:**
- Queries bookings table for same kitchen_id
- Filters by status IN ('pending', 'confirmed')
- Checks for time overlap using SQL range queries
- Returns user-friendly error if conflict detected
- Prevents wasted Stripe API calls for unavailable slots

### Document Management

```typescript
// Upload document file to storage
uploadDocumentFile(file: File, kitchenId: string, documentType: DocumentType)

// Create document record after upload
createKitchenDocument(kitchenId: string, documentType: DocumentType, fileUrl: string, fileName: string)

// Get documents for a kitchen (owners)
getKitchenDocuments(kitchenId: string)

// Get all pending documents (admins)
getPendingDocuments()

// Review document (admins)
reviewDocument(documentId: string, status: 'approved' | 'rejected', reviewNotes?: string)

// Get compliance status for a kitchen
getKitchenComplianceStatus(kitchenId: string)
```

## User Flows

### Owner Flow
1. Sign up with role "owner"
2. Create kitchen
3. Navigate to "Compliance Documents" from kitchen card
4. Upload health permit PDF
5. Upload insurance certificate PDF
6. Wait for admin review
7. Receive approval
8. Kitchen becomes visible in search and bookable

### Admin Flow
1. Admin user logs in
2. Navigate to `/admin/compliance`
3. Review pending documents:
   - View document file
   - Add review notes
   - Approve or reject
4. Documents disappear from queue after review
5. Kitchen compliance auto-updates

### Tenant Flow
1. Sign up with role "tenant"
2. Browse kitchens at `/kitchens`
3. Only see compliant kitchens
4. Book kitchen with payment
5. View booking in `/renter/bookings`

## Security Features

### Row Level Security (RLS) Policies

```sql
-- Owners can only upload documents for their own kitchens
-- Admins can view and review all documents
-- Tenants cannot access document management
-- Kitchen visibility controlled by compliance_approved flag
```

### File Upload Security
- File validation on client and server
- Scoped to authenticated users only
- Namespaced by kitchen ID
- RLS policies on storage bucket

### Role Enforcement
- Role set during signup via user metadata
- Role checked on all sensitive operations
- Admin-only routes protected by profile role check

## Database Triggers

### `on_document_status_change`
- **Fires**: After INSERT or UPDATE on `kitchen_documents`
- **Action**: Calls `update_kitchen_compliance()`
- **Effect**: Updates kitchen `compliance_approved = true` when both documents approved

### `on_auth_user_created` (modified)
- **Fires**: After INSERT on `auth.users`
- **Action**: Calls `handle_new_user()`
- **Effect**: Creates profile with role from user metadata

## Performance Considerations

- Indexed fields: `role`, `status`, `kitchen_id`, `reviewer_id`
- Document queries use RLS for automatic filtering
- Storage bucket public URLs avoid auth overhead
- Revalidation paths ensure fresh data after mutations

## Known Limitations

1. **No file size limits enforced**: Add client/server validation
2. **No file type validation**: Only accepts common formats
3. **No document expiry dates**: Add future feature
4. **Manual admin creation**: Need admin invitation flow
5. **No email notifications**: Add for document status changes

## Future Enhancements

- [ ] Email notifications when documents reviewed
- [ ] Document expiry dates and renewal reminders
- [ ] Bulk document approval for admins
- [ ] Document versioning (re-upload after rejection)
- [ ] Admin dashboard analytics
- [ ] Automated OCR for document validation
- [ ] Mobile app support for document scanning

## Troubleshooting

### Kitchen not appearing in search after approval
- Check `compliance_approved` flag: `SELECT compliance_approved FROM kitchens WHERE id = '[kitchen-id]'`
- Verify both documents approved: `SELECT document_type, status FROM kitchen_documents WHERE kitchen_id = '[kitchen-id]'`
- Trigger may not have fired - manually update: `UPDATE kitchens SET compliance_approved = true WHERE id = '[kitchen-id]'`

### Document upload fails
- Check storage bucket exists and is public
- Verify RLS policies on storage bucket
- Check user owns the kitchen
- Verify file size under limit

### Admin cannot see pending documents
- Verify user role is 'admin': `SELECT role FROM profiles WHERE id = auth.uid()`
- Check RLS policies allow admin SELECT on kitchen_documents
- Verify documents exist with status = 'pending'

### Role not set on signup
- Verify migration updated `handle_new_user()` function
- Check signup code passes role in `options.data.role`
- Manually update role: `UPDATE profiles SET role = 'owner' WHERE email = '[email]'`

## Support

For issues or questions:
1. Check test plan: `tests/MVP_COMPLIANCE_E2E_TEST_PLAN.md`
2. Review requirements: `docs/MVP_85_VERTICAL_SLICE.md`
3. Inspect database schema: `supabase/migration_mvp_compliance.sql`
4. Open issue in project repository

---

**Version**: 1.0
**Last Updated**: 2025-12-10
**Implementation**: MVP 85% Vertical Slice
