# Prep MVP v1.0 - Project Management Tickets

**Format**: GitHub Issues / Linear / Jira compatible

---

## Week 0: Infrastructure Setup (Priority: Critical)

### PREP-001: Create Supabase Project and Apply Schema
**Priority**: P0 (Critical)
**Estimate**: 2 hours
**Labels**: infrastructure, database, week-0

**Description:**
Set up production and staging Supabase projects for PostgreSQL database.

**Acceptance Criteria:**
- [ ] Supabase project created for production
- [ ] Supabase project created for staging
- [ ] `prepchef/db/schema.sql` applied to both environments
- [ ] All extensions enabled (uuid-ossp, citext, btree_gist, postgis)
- [ ] Row-Level Security policies configured
- [ ] Connection strings stored in secrets manager

**Technical Notes:**
- Use Supabase CLI: `supabase init`
- Database URL format: `postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres`

---

### PREP-002: Install and Configure Prisma ORM
**Priority**: P0 (Critical)
**Estimate**: 3 hours
**Labels**: infrastructure, database, orm, week-0

**Description:**
Install Prisma ORM and generate client from existing PostgreSQL schema.

**Acceptance Criteria:**
- [ ] Prisma installed: `npm install prisma @prisma/client`
- [ ] `prisma/schema.prisma` created and matches SQL schema
- [ ] Prisma client generated: `npx prisma generate`
- [ ] Database connection tested
- [ ] Environment variables configured (.env.example created)
- [ ] Migration strategy documented

**Technical Notes:**
- Use `npx prisma db pull` to introspect existing database
- Configure connection pooling for production
- Document migration workflow in README

**Related Files:**
- `prepchef/prisma/schema.prisma`
- `prepchef/.env.example`

---

### PREP-003: Set Up Docker Compose for Local Development
**Priority**: P0 (Critical)
**Estimate**: 2 hours
**Labels**: infrastructure, docker, week-0

**Description:**
Create Docker Compose configuration for local development environment.

**Acceptance Criteria:**
- [ ] `docker-compose.yml` created with PostgreSQL, Redis, MinIO, MailHog
- [ ] Services start successfully: `docker-compose up -d`
- [ ] Health checks passing for all services
- [ ] README updated with Docker setup instructions
- [ ] Seed data script created

**Services:**
- PostgreSQL 15 with PostGIS (port 5432)
- Redis 7 (port 6379)
- MinIO (ports 9000, 9001)
- MailHog (ports 1025, 8025)

**Related Files:**
- `docker-compose.yml`
- `prepchef/README.md`

---

### PREP-004: Configure GitHub Actions CI/CD Pipeline
**Priority**: P1 (High)
**Estimate**: 4 hours
**Labels**: infrastructure, ci-cd, week-0

**Description:**
Set up GitHub Actions workflow for automated testing and deployment.

**Acceptance Criteria:**
- [ ] `.github/workflows/ci.yml` created
- [ ] Lint check runs on every PR
- [ ] TypeScript type check runs on every PR
- [ ] Unit tests run with PostgreSQL/Redis test containers
- [ ] Staging deployment configured (develop branch)
- [ ] Production deployment configured (main branch, manual approval)
- [ ] Code coverage reporting enabled

**Jobs:**
1. Lint & Format Check
2. TypeScript Type Check
3. Backend Tests (with test DB)
4. Frontend Tests
5. Build All Packages
6. Deploy to Staging (auto)
7. Deploy to Production (manual)

**Related Files:**
- `.github/workflows/ci.yml`

---

### PREP-005: Configure Secrets Management (Doppler/Fly)
**Priority**: P1 (High)
**Estimate**: 2 hours
**Labels**: infrastructure, security, week-0

**Description:**
Set up secrets management for development, staging, and production environments.

**Acceptance Criteria:**
- [ ] Doppler project created (or Fly.io secrets configured)
- [ ] All required secrets documented in `.env.example`
- [ ] Development secrets configured locally
- [ ] Staging secrets set in Fly.io
- [ ] Production secrets set in Fly.io
- [ ] Secret rotation policy documented

**Required Secrets:**
- DATABASE_URL
- JWT_SECRET, JWT_REFRESH_SECRET
- STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
- RESEND_API_KEY
- SUPABASE_URL, SUPABASE_SERVICE_KEY
- GOOGLE_MAPS_API_KEY

---

## Week 1-2: Authentication & User Management

### PREP-010: Implement User Registration with bcrypt
**Priority**: P0 (Critical)
**Estimate**: 5 hours
**Labels**: auth, backend, week-1

**Description:**
Build user registration endpoint with password hashing and email verification.

**Acceptance Criteria:**
- [ ] `POST /api/auth/register` endpoint created
- [ ] Password validation (zxcvbn strength check ≥3)
- [ ] Passwords hashed with bcrypt (saltRounds: 12)
- [ ] Email uniqueness check
- [ ] Verification token generated and stored
- [ ] Welcome email sent via Resend
- [ ] Rate limiting applied (5 requests/hour per IP)

**API Contract:**
```typescript
POST /api/auth/register
Body: { email, password, fullName, role }
Response: { userId, message: "Verification email sent" }
```

**Related Files:**
- `prepchef/services/auth-svc/src/api/auth.ts`
- `prepchef/services/auth-svc/src/lib/password.ts`

---

### PREP-011: Implement JWT Authentication
**Priority**: P0 (Critical)
**Estimate**: 4 hours
**Labels**: auth, backend, week-1

**Description:**
Create login endpoint with JWT access/refresh token flow.

**Acceptance Criteria:**
- [ ] `POST /api/auth/login` endpoint created
- [ ] Email + password validation
- [ ] Short-lived access token generated (15 min)
- [ ] Long-lived refresh token generated (7 days)
- [ ] Tokens stored in httpOnly cookies
- [ ] Failed login attempts logged (audit trail)
- [ ] Rate limiting applied (10 requests/15min per IP)

**API Contract:**
```typescript
POST /api/auth/login
Body: { email, password }
Response: { accessToken, refreshToken, user }
Set-Cookie: accessToken=...; httpOnly; secure
Set-Cookie: refreshToken=...; httpOnly; secure
```

---

### PREP-012: Build Email Verification Flow
**Priority**: P0 (Critical)
**Estimate**: 3 hours
**Labels**: auth, backend, week-1

**Description:**
Implement email verification link handling.

**Acceptance Criteria:**
- [ ] `GET /api/auth/verify/:token` endpoint created
- [ ] Token validation (24-hour expiry)
- [ ] User verified status updated in database
- [ ] Verification email template created (Resend)
- [ ] Resend verification endpoint: `POST /api/auth/resend-verification`
- [ ] Expired token handling

---

### PREP-013: Implement Password Reset Flow
**Priority**: P1 (High)
**Estimate**: 4 hours
**Labels**: auth, backend, week-1

**Description:**
Build password reset functionality.

**Acceptance Criteria:**
- [ ] `POST /api/auth/forgot-password` endpoint created
- [ ] Reset token generated and emailed
- [ ] `POST /api/auth/reset-password/:token` endpoint created
- [ ] Password reset email template created
- [ ] Old password invalidated after reset
- [ ] Token single-use enforced

---

### PREP-014: Create Auth Middleware & RBAC
**Priority**: P0 (Critical)
**Estimate**: 4 hours
**Labels**: auth, backend, middleware, week-2

**Description:**
Build authentication middleware and role-based access control.

**Acceptance Criteria:**
- [ ] `requireAuth` middleware created
- [ ] `requireRole(roles[])` middleware created
- [ ] JWT verification from cookies
- [ ] User object attached to request context
- [ ] Unauthorized requests return 401
- [ ] Forbidden requests return 403
- [ ] Audit logging for protected route access

**Usage Example:**
```typescript
app.get('/api/admin/users',
  requireAuth,
  requireRole(['admin']),
  listUsersHandler
);
```

---

### PREP-015: Build Frontend Login/Signup Forms
**Priority**: P0 (Critical)
**Estimate**: 6 hours
**Labels**: auth, frontend, week-2

**Description:**
Create React components for authentication flows.

**Acceptance Criteria:**
- [ ] Login form with React Hook Form + Zod validation
- [ ] Signup form with password strength indicator
- [ ] Email verification screen
- [ ] Forgot password flow
- [ ] Form error handling
- [ ] Loading states
- [ ] Accessible (WCAG 2.1 AA)

**Components:**
- `LoginForm.tsx`
- `SignupForm.tsx`
- `VerifyEmailPage.tsx`
- `ForgotPasswordForm.tsx`
- `ResetPasswordForm.tsx`

**Related Files:**
- `apps/web/src/components/auth/`
- `apps/web/src/pages/auth/`

---

### PREP-016: Create Auth Store (Zustand)
**Priority**: P0 (Critical)
**Estimate**: 3 hours
**Labels**: auth, frontend, state-management, week-2

**Description:**
Build Zustand store for authentication state.

**Acceptance Criteria:**
- [ ] Auth store created with Zustand
- [ ] User object persisted to localStorage
- [ ] Login/logout actions
- [ ] Token refresh logic
- [ ] Protected route wrapper component
- [ ] Unauthorized redirect to login

**Store Interface:**
```typescript
interface AuthStore {
  user: User | null;
  isAuthenticated: boolean;
  login: (email, password) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
}
```

**Related Files:**
- `apps/web/src/stores/authStore.ts`
- `apps/web/src/components/ProtectedRoute.tsx`

---

### PREP-017: Write Auth Integration Tests
**Priority**: P1 (High)
**Estimate**: 4 hours
**Labels**: auth, testing, week-2

**Description:**
Create integration tests for authentication flows.

**Acceptance Criteria:**
- [ ] Test: User registration happy path
- [ ] Test: Login with valid credentials
- [ ] Test: Login with invalid credentials (rate limited)
- [ ] Test: JWT token refresh
- [ ] Test: Email verification
- [ ] Test: Password reset
- [ ] Test coverage ≥80% for auth module

**Related Files:**
- `prepchef/services/auth-svc/src/__tests__/`

---

## Week 3: Kitchen Listings CRUD

### PREP-020: Implement Kitchen Listings API
**Priority**: P0 (Critical)
**Estimate**: 8 hours
**Labels**: listings, backend, week-3

**Description:**
Build CRUD API for kitchen listings.

**Acceptance Criteria:**
- [ ] `POST /api/kitchens` - Create listing (host-only)
- [ ] `GET /api/kitchens` - List with pagination & filters
- [ ] `GET /api/kitchens/:id` - Get single listing
- [ ] `PATCH /api/kitchens/:id` - Update listing (host/admin)
- [ ] `DELETE /api/kitchens/:id` - Soft delete (host/admin)
- [ ] Input validation with Zod
- [ ] Owner authorization checks
- [ ] Audit logging

**API Contracts:**
See `TECHNICAL_OUTLINE.md` Section 3.3 for full specifications.

---

### PREP-021: Implement Geospatial Search (PostGIS)
**Priority**: P0 (Critical)
**Estimate**: 6 hours
**Labels**: listings, backend, geospatial, week-3

**Description:**
Build location-based search using PostGIS.

**Acceptance Criteria:**
- [ ] Radius search: `GET /api/kitchens?lat=X&lng=Y&radius=10km`
- [ ] Bounding box search: `GET /api/kitchens?bounds=[[lat,lng],[lat,lng]]`
- [ ] Distance calculation in results
- [ ] Indexed for performance (GiST index on location column)
- [ ] Sort by distance

**Query Example:**
```sql
SELECT * FROM venues
WHERE ST_DWithin(
  location,
  ST_MakePoint($lng, $lat)::geography,
  $radius_meters
)
ORDER BY ST_Distance(location, ST_MakePoint($lng, $lat)::geography);
```

---

### PREP-022: Implement Photo Upload (Supabase Storage)
**Priority**: P0 (Critical)
**Estimate**: 5 hours
**Labels**: listings, backend, storage, week-3

**Description:**
Build photo upload flow with Supabase Storage.

**Acceptance Criteria:**
- [ ] Signed URL generation: `POST /api/kitchens/:id/upload-url`
- [ ] Client-side image compression (max 2MB)
- [ ] Max 10 photos per listing
- [ ] Supported formats: JPG, PNG, WebP
- [ ] Thumbnail generation (400x300)
- [ ] Photo deletion endpoint
- [ ] Storage bucket created with CDN enabled

---

### PREP-023: Build Kitchen Listing Editor (Frontend)
**Priority**: P0 (Critical)
**Estimate**: 10 hours
**Labels**: listings, frontend, week-3

**Description:**
Create multi-step form wizard for creating/editing listings.

**Acceptance Criteria:**
- [ ] Multi-step form with progress indicator
- [ ] Step 1: Basic Info (title, description, kitchen type)
- [ ] Step 2: Location (address autocomplete with Google Places)
- [ ] Step 3: Pricing (hourly/daily/weekly rates)
- [ ] Step 4: Equipment (checklist with search)
- [ ] Step 5: Photos (drag-and-drop upload)
- [ ] Form persistence (save draft to localStorage)
- [ ] Validation on each step
- [ ] Accessible and responsive

**Components:**
- `KitchenEditor.tsx`
- `ListingForm/` (multi-step components)
- `PhotoUpload.tsx`
- `EquipmentSelector.tsx`

**Related Files:**
- `apps/web/src/pages/host/KitchenEditor.tsx`
- `apps/web/src/components/listings/`

---

### PREP-024: Build Kitchen Browser & Search UI
**Priority**: P0 (Critical)
**Estimate**: 8 hours
**Labels**: listings, frontend, week-3

**Description:**
Create kitchen discovery and search interface.

**Acceptance Criteria:**
- [ ] Search bar with location autocomplete
- [ ] Filter panel (price, equipment, certifications)
- [ ] Grid/list view toggle
- [ ] Pagination (infinite scroll)
- [ ] Loading skeletons
- [ ] Empty state handling
- [ ] Responsive design

**Components:**
- `KitchenBrowser.tsx`
- `SearchBar.tsx`
- `FilterPanel.tsx`
- `KitchenCard.tsx`

---

### PREP-025: Build Kitchen Detail Page
**Priority**: P0 (Critical)
**Estimate**: 6 hours
**Labels**: listings, frontend, week-3

**Description:**
Create detailed kitchen listing page.

**Acceptance Criteria:**
- [ ] Photo gallery with lightbox
- [ ] Kitchen details (equipment, features, restrictions)
- [ ] Pricing information
- [ ] Availability calendar preview
- [ ] Reviews section
- [ ] "Book Now" CTA
- [ ] Share button
- [ ] Map with location pin

**Components:**
- `KitchenDetail.tsx`
- `PhotoGallery.tsx`
- `AvailabilityCalendar.tsx`
- `ReviewsList.tsx`

---

## Week 4: Compliance & Certification

### PREP-030: Build Document Upload API
**Priority**: P0 (Critical)
**Estimate**: 5 hours
**Labels**: compliance, backend, week-4

**Description:**
Create API for uploading compliance documents.

**Acceptance Criteria:**
- [ ] `POST /api/compliance/documents` - Upload document
- [ ] `GET /api/compliance/documents/:id` - Get document
- [ ] `DELETE /api/compliance/documents/:id` - Delete document
- [ ] Supported types: health_permit, business_license, insurance
- [ ] PDF/JPG/PNG formats only
- [ ] Max file size: 10MB
- [ ] Expiry date tracking
- [ ] Status: pending → approved/rejected

---

### PREP-031: Build Admin Review Queue
**Priority**: P0 (Critical)
**Estimate**: 6 hours
**Labels**: compliance, backend, admin, week-4

**Description:**
Create admin panel for document review.

**Acceptance Criteria:**
- [ ] `GET /api/admin/compliance/pending` - List pending documents
- [ ] `POST /api/admin/compliance/:id/approve` - Approve document
- [ ] `POST /api/admin/compliance/:id/reject` - Reject with reason
- [ ] Email notification to host on status change
- [ ] Audit log of all review actions
- [ ] Filter by document type and status

---

### PREP-032: Implement Document Expiry Tracking
**Priority**: P1 (High)
**Estimate**: 4 hours
**Labels**: compliance, backend, cron, week-4

**Description:**
Create cron job for tracking and alerting on expiring documents.

**Acceptance Criteria:**
- [ ] Daily cron job checks for expiring documents
- [ ] Email sent 30 days before expiry
- [ ] Email sent 7 days before expiry
- [ ] Listing automatically suspended on expiry
- [ ] Admin notification for expired documents
- [ ] BullMQ job queue for email sending

---

### PREP-033: Build Compliance Upload UI (Host Dashboard)
**Priority**: P0 (Critical)
**Estimate**: 5 hours
**Labels**: compliance, frontend, week-4

**Description:**
Create document upload interface for hosts.

**Acceptance Criteria:**
- [ ] Drag-and-drop file upload
- [ ] File type validation
- [ ] Upload progress indicator
- [ ] Document list with status badges
- [ ] Expiry date input
- [ ] Download uploaded document
- [ ] Delete document (if not approved)

**Components:**
- `ComplianceUpload.tsx`
- `DocumentList.tsx`
- `DocumentStatusBadge.tsx`

---

### PREP-034: Build Admin Review Queue UI
**Priority**: P0 (Critical)
**Estimate**: 6 hours
**Labels**: compliance, frontend, admin, week-4

**Description:**
Create admin interface for reviewing compliance documents.

**Acceptance Criteria:**
- [ ] Table view with filters (pending/approved/rejected)
- [ ] Document preview (PDF viewer)
- [ ] Approve/reject buttons
- [ ] Rejection reason modal
- [ ] Bulk approve functionality
- [ ] Action history timeline
- [ ] Keyboard shortcuts for review workflow

**Components:**
- `AdminReviewQueue.tsx`
- `DocumentPreview.tsx`
- `RejectionReasonModal.tsx`

---

## Week 5: Availability Management

### PREP-040: Implement Availability API
**Priority**: P0 (Critical)
**Estimate**: 8 hours
**Labels**: availability, backend, week-5

**Description:**
Build API for managing kitchen availability schedules.

**Acceptance Criteria:**
- [ ] `POST /api/kitchens/:id/availability` - Set recurring hours
- [ ] `GET /api/kitchens/:id/availability` - Get available slots
- [ ] `DELETE /api/availability/:id` - Remove availability window
- [ ] Support for recurring schedules (weekly)
- [ ] Support for one-off date blocks
- [ ] Buffer time between bookings (configurable)
- [ ] Conflict detection

**Data Model:**
```typescript
interface AvailabilityWindow {
  dayOfWeek: 0-6; // 0=Sunday
  startTime: "09:00";
  endTime: "17:00";
  isRecurring: boolean;
  startDate?: Date;
  endDate?: Date;
}
```

---

### PREP-041: Implement Redis Availability Cache
**Priority**: P1 (High)
**Estimate**: 5 hours
**Labels**: availability, backend, redis, week-5

**Description:**
Add Redis caching layer for availability lookups.

**Acceptance Criteria:**
- [ ] Cache key format: `availability:{kitchen_id}:{window_id}`
- [ ] Cache TTL aligned with `updated_at` timestamp
- [ ] Write-through cache updates
- [ ] Cache invalidation on booking creation/cancellation
- [ ] Fallback to PostgreSQL on cache miss
- [ ] Monitor cache hit rate (Grafana dashboard)

---

### PREP-042: Build Calendar UI Component
**Priority**: P0 (Critical)
**Estimate**: 8 hours
**Labels**: availability, frontend, week-5

**Description:**
Create reusable calendar component for availability management.

**Acceptance Criteria:**
- [ ] Weekly recurring hours picker
- [ ] Date range blocking (e.g., vacation dates)
- [ ] Hover preview of available time slots
- [ ] Mobile-responsive
- [ ] Timezone handling
- [ ] Export to ICS calendar file

**Components:**
- `AvailabilityCalendar.tsx`
- `WeeklySchedulePicker.tsx`
- `DateRangeBlocker.tsx`

---

### PREP-043: Build Host Availability Manager UI
**Priority**: P0 (Critical)
**Estimate**: 6 hours
**Labels**: availability, frontend, week-5

**Description:**
Create host dashboard section for managing availability.

**Acceptance Criteria:**
- [ ] Visual weekly schedule editor
- [ ] Add/edit/delete availability windows
- [ ] One-off date blocking
- [ ] Preview upcoming bookings on calendar
- [ ] Save and publish changes
- [ ] Undo/redo functionality

**Components:**
- `HostAvailabilityManager.tsx`
- `ScheduleEditor.tsx`

---

## Week 6: Search & Discovery

### PREP-050: Implement Full-Text Search
**Priority**: P0 (Critical)
**Estimate**: 5 hours
**Labels**: search, backend, week-6

**Description:**
Add full-text search to kitchen listings.

**Acceptance Criteria:**
- [ ] PostgreSQL `tsvector` index on title + description
- [ ] Search query: `GET /api/kitchens?q=pizza+commercial`
- [ ] Fuzzy matching support
- [ ] Search result highlighting
- [ ] Sort by relevance
- [ ] Combined with geospatial filters

**SQL Example:**
```sql
SELECT * FROM kitchen_listings
WHERE to_tsvector('english', title || ' ' || description) @@ to_tsquery('pizza & commercial')
ORDER BY ts_rank(to_tsvector('english', title || ' ' || description), to_tsquery('pizza & commercial')) DESC;
```

---

### PREP-051: Implement Advanced Filters
**Priority**: P0 (Critical)
**Estimate**: 4 hours
**Labels**: search, backend, week-6

**Description:**
Add multi-faceted filtering to search API.

**Acceptance Criteria:**
- [ ] Price range filter: `?minPrice=50&maxPrice=200`
- [ ] Equipment filter: `?equipment=oven,mixer,freezer`
- [ ] Certification filter: `?certifications=health_permit`
- [ ] Availability filter: `?availableFrom=2025-11-01&availableTo=2025-11-02`
- [ ] Features filter: `?features=parking,loading-dock`
- [ ] Combine multiple filters (AND logic)

---

### PREP-052: Integrate Google Maps API
**Priority**: P0 (Critical)
**Estimate**: 5 hours
**Labels**: search, frontend, maps, week-6

**Description:**
Add Google Maps integration for location-based search.

**Acceptance Criteria:**
- [ ] Map view of search results
- [ ] Kitchen location pins with preview popup
- [ ] Current location button
- [ ] Draw radius around location
- [ ] Click pin to open kitchen detail
- [ ] Cluster markers for performance

**Components:**
- `MapView.tsx`
- `KitchenMarker.tsx`
- `MapControls.tsx`

---

### PREP-053: Build Search Results UI
**Priority**: P0 (Critical)
**Estimate**: 6 hours
**Labels**: search, frontend, week-6

**Description:**
Create polished search results interface.

**Acceptance Criteria:**
- [ ] Search results count
- [ ] Sort dropdown (price, distance, rating)
- [ ] Filter chips (removable)
- [ ] Loading states
- [ ] Empty state with suggestions
- [ ] Pagination controls
- [ ] Save search functionality

**Components:**
- `SearchResults.tsx`
- `FilterChips.tsx`
- `SortDropdown.tsx`

---

## Week 7: Booking Flow & Payments

### PREP-060: Integrate Stripe Payment Intents
**Priority**: P0 (Critical)
**Estimate**: 8 hours
**Labels**: payments, backend, stripe, week-7

**Description:**
Implement Stripe Payment Intents for booking payments.

**Acceptance Criteria:**
- [ ] Stripe SDK installed and configured
- [ ] `POST /api/payments/intents` - Create payment intent
- [ ] `POST /api/payments/confirm` - Confirm payment
- [ ] Webhook handler: `POST /webhooks/stripe`
- [ ] Handle payment_intent.succeeded
- [ ] Handle payment_intent.payment_failed
- [ ] Store payment intent ID in bookings table

---

### PREP-061: Implement Booking Creation API
**Priority**: P0 (Critical)
**Estimate**: 10 hours
**Labels**: booking, backend, week-7

**Description:**
Build comprehensive booking creation flow.

**Acceptance Criteria:**
- [ ] `POST /api/bookings` - Create booking with payment
- [ ] Validate availability (Redis + PostgreSQL)
- [ ] Prevent double-booking (PostgreSQL exclusion constraint)
- [ ] Calculate pricing (call pricing-svc)
- [ ] Create payment intent (Stripe)
- [ ] Send confirmation email
- [ ] Booking status: requested → payment_authorized → confirmed
- [ ] Rollback on payment failure

**Flow:**
1. Validate availability
2. Lock time slot (Redis distributed lock)
3. Create booking record (status: requested)
4. Create payment intent (Stripe)
5. Return payment intent client secret
6. Frontend confirms payment
7. Webhook updates booking status → confirmed
8. Send confirmation email
9. Release lock

---

### PREP-062: Implement Booking Conflict Detection
**Priority**: P0 (Critical)
**Estimate**: 6 hours
**Labels**: booking, backend, week-7

**Description:**
Build robust conflict detection to prevent double-bookings.

**Acceptance Criteria:**
- [ ] PostgreSQL exclusion constraint on time ranges
- [ ] Redis distributed lock during booking creation
- [ ] Automatic reconciliation job (daily)
- [ ] Manual override tooling for ops
- [ ] Conflict error returns 409 with available slots
- [ ] Integration tests for race conditions

---

### PREP-063: Build Checkout Flow UI
**Priority**: P0 (Critical)
**Estimate**: 10 hours
**Labels**: booking, frontend, week-7

**Description:**
Create seamless booking checkout experience.

**Acceptance Criteria:**
- [ ] Date/time picker with availability checks
- [ ] Real-time pricing calculator
- [ ] Stripe Elements payment form
- [ ] Guest count and special requests
- [ ] Booking summary panel
- [ ] Confirmation screen
- [ ] Error handling (payment failed, slot taken)
- [ ] 3D Secure (SCA) support

**Components:**
- `BookingCheckout.tsx`
- `DateTimePicker.tsx`
- `PricingCalculator.tsx`
- `PaymentForm.tsx`
- `BookingConfirmation.tsx`

---

### PREP-064: Implement Notification Service
**Priority**: P0 (Critical)
**Estimate**: 6 hours
**Labels**: notifications, backend, week-7

**Description:**
Build email notification system with Resend.

**Acceptance Criteria:**
- [ ] Resend SDK configured
- [ ] Email templates created (Handlebars/React Email)
- [ ] Booking confirmation email
- [ ] Booking reminder (24h before)
- [ ] Booking cancellation email
- [ ] BullMQ queue for async sending
- [ ] Retry logic (3 attempts, exponential backoff)

**Email Templates:**
- `booking-confirmation.hbs`
- `booking-reminder.hbs`
- `booking-cancellation.hbs`
- `payment-failed.hbs`

---

### PREP-065: Build User Dashboard
**Priority**: P0 (Critical)
**Estimate**: 8 hours
**Labels**: booking, frontend, week-7

**Description:**
Create renter dashboard for managing bookings.

**Acceptance Criteria:**
- [ ] Upcoming bookings list
- [ ] Past bookings list
- [ ] Booking detail modal
- [ ] Cancel booking button
- [ ] Download invoice (PDF)
- [ ] Messages inbox
- [ ] Payment methods management

**Components:**
- `UserDashboard.tsx`
- `BookingsList.tsx`
- `BookingDetailModal.tsx`
- `MessagesInbox.tsx`

---

### PREP-066: Build Host Dashboard
**Priority**: P0 (Critical)
**Estimate**: 8 hours
**Labels**: booking, frontend, week-7

**Description:**
Create host dashboard for managing bookings and listings.

**Acceptance Criteria:**
- [ ] Calendar view of bookings
- [ ] Earnings summary (today, week, month)
- [ ] Active listings with quick edit
- [ ] Booking requests (approve/decline)
- [ ] Messages inbox
- [ ] Analytics (utilization rate, revenue trends)

**Components:**
- `HostDashboard.tsx`
- `BookingsCalendar.tsx`
- `EarningsSummary.tsx`
- `ListingsManager.tsx`

---

## Week 8: Messaging & Polish

### PREP-070: Implement Messaging API
**Priority**: P1 (High)
**Estimate**: 6 hours
**Labels**: messaging, backend, week-8

**Description:**
Build direct messaging between renters and hosts.

**Acceptance Criteria:**
- [ ] `POST /api/messages` - Send message
- [ ] `GET /api/messages/:conversationId` - Get thread
- [ ] `GET /api/conversations` - List conversations
- [ ] `PATCH /api/messages/:id/read` - Mark as read
- [ ] Attach to booking context
- [ ] Soft delete support
- [ ] Pagination (cursor-based)

---

### PREP-071: Implement Real-Time Messaging (Socket.IO)
**Priority**: P1 (High)
**Estimate**: 6 hours
**Labels**: messaging, backend, real-time, week-8

**Description:**
Add real-time message delivery with Socket.IO.

**Acceptance Criteria:**
- [ ] Socket.IO server configured
- [ ] Authentication via JWT
- [ ] Room-based messaging (conversation_id)
- [ ] Message event: `message:new`
- [ ] Typing indicator: `typing:start`, `typing:stop`
- [ ] Online status tracking
- [ ] Reconnection handling

---

### PREP-072: Build Messages UI
**Priority**: P1 (High)
**Estimate**: 8 hours
**Labels**: messaging, frontend, week-8

**Description:**
Create messaging interface for renter/host communication.

**Acceptance Criteria:**
- [ ] Conversation list with unread count
- [ ] Message thread view
- [ ] Real-time message updates
- [ ] Typing indicator
- [ ] Send message form
- [ ] Message timestamps (relative)
- [ ] Attachment support (images)
- [ ] Mobile-responsive

**Components:**
- `MessagesInbox.tsx`
- `ConversationList.tsx`
- `MessageThread.tsx`
- `MessageInput.tsx`

---

## Week 9: Stripe Connect & Payouts

### PREP-080: Implement Stripe Connect Onboarding
**Priority**: P0 (Critical)
**Estimate**: 10 hours
**Labels**: payments, backend, stripe-connect, week-9

**Description:**
Build Stripe Connect Custom account onboarding for hosts.

**Acceptance Criteria:**
- [ ] Create Connect account: `POST /api/connect/accounts`
- [ ] Generate account link: `POST /api/connect/account-link`
- [ ] Handle onboarding webhooks
- [ ] Store account ID in hosts table
- [ ] Track KYC verification status
- [ ] Onboarding completion notification

**Stripe Connect Flow:**
1. Host clicks "Enable Payouts"
2. Create Stripe Connect account
3. Redirect to Stripe onboarding
4. Handle return URL
5. Verify account capabilities
6. Enable payout flows

---

### PREP-081: Implement Automatic Payouts
**Priority**: P0 (Critical)
**Estimate**: 8 hours
**Labels**: payments, backend, week-9

**Description:**
Build automatic payout system after booking completion.

**Acceptance Criteria:**
- [ ] Booking completion triggers payout
- [ ] Calculate platform commission (20%)
- [ ] Create Stripe Transfer to host account
- [ ] Record transaction in payments table
- [ ] Retry logic for failed payouts (BullMQ)
- [ ] Email notification on payout success/failure
- [ ] Finance ledger for audit trail

**Payout Calculation:**
```
Total Booking Amount: $100
Platform Fee (20%):   -$20
Host Payout:          $80
```

---

### PREP-082: Build Connect Onboarding UI
**Priority**: P0 (Critical)
**Estimate**: 6 hours
**Labels**: payments, frontend, week-9

**Description:**
Create UI for Stripe Connect onboarding.

**Acceptance Criteria:**
- [ ] "Enable Payouts" button on host dashboard
- [ ] Onboarding status indicator
- [ ] Progress tracker (pending, in_review, verified)
- [ ] Re-verification prompt if needed
- [ ] Support contact link

**Components:**
- `ConnectOnboarding.tsx`
- `PayoutSettings.tsx`
- `AccountStatus.tsx`

---

### PREP-083: Build Earnings Dashboard
**Priority**: P1 (High)
**Estimate**: 6 hours
**Labels**: payments, frontend, week-9

**Description:**
Create host earnings dashboard.

**Acceptance Criteria:**
- [ ] Total earnings (all-time, month, week)
- [ ] Pending payouts list
- [ ] Completed payouts list
- [ ] Export to CSV
- [ ] Filter by date range
- [ ] Earnings chart (daily/weekly/monthly)

**Components:**
- `EarningsDashboard.tsx`
- `PayoutHistory.tsx`
- `EarningsChart.tsx`

---

## Week 10: Reviews, Hardening & Launch

### PREP-090: Implement Review System API
**Priority**: P0 (Critical)
**Estimate**: 6 hours
**Labels**: reviews, backend, week-10

**Description:**
Build two-sided review system.

**Acceptance Criteria:**
- [ ] `POST /api/bookings/:id/review` - Submit review
- [ ] `GET /api/kitchens/:id/reviews` - Get listing reviews
- [ ] Review unlock 24h after booking completion
- [ ] 5-star rating with categories (cleanliness, equipment, location, value)
- [ ] Photo upload support
- [ ] Host response feature
- [ ] Abuse reporting

---

### PREP-091: Build Reviews UI
**Priority**: P0 (Critical)
**Estimate**: 6 hours
**Labels**: reviews, frontend, week-10

**Description:**
Create review submission and display components.

**Acceptance Criteria:**
- [ ] Star rating input component
- [ ] Review form with photos
- [ ] Reviews list on kitchen detail page
- [ ] Host response display
- [ ] Helpful button
- [ ] Report abuse button
- [ ] Sort by rating/date

**Components:**
- `ReviewForm.tsx`
- `ReviewsList.tsx`
- `StarRating.tsx`

---

### PREP-092: Implement Admin Analytics Dashboard
**Priority**: P1 (High)
**Estimate**: 8 hours
**Labels**: admin, analytics, week-10

**Description:**
Build admin dashboard with platform metrics.

**Acceptance Criteria:**
- [ ] Total users (renters, hosts, growth rate)
- [ ] Total bookings (completed, canceled, revenue)
- [ ] Most booked kitchens (top 10)
- [ ] Certification status heatmap
- [ ] Revenue trends chart
- [ ] Utilization rate by kitchen
- [ ] Export reports to CSV

**Components:**
- `AdminDashboard.tsx`
- `MetricsCards.tsx`
- `RevenueChart.tsx`
- `UtilizationChart.tsx`

---

### PREP-093: Configure Error Tracking (Sentry)
**Priority**: P0 (Critical)
**Estimate**: 3 hours
**Labels**: infrastructure, monitoring, week-10

**Description:**
Set up Sentry for error tracking and monitoring.

**Acceptance Criteria:**
- [ ] Sentry SDK installed (backend + frontend)
- [ ] Source maps uploaded for stack traces
- [ ] User context attached to errors
- [ ] Breadcrumbs enabled
- [ ] Release tracking configured
- [ ] PagerDuty integration for Sev1 alerts

---

### PREP-094: Configure Monitoring Dashboards (Grafana)
**Priority**: P1 (High)
**Estimate**: 4 hours
**Labels**: infrastructure, monitoring, week-10

**Description:**
Set up Grafana dashboards for key metrics.

**Acceptance Criteria:**
- [ ] API latency (p50, p95, p99)
- [ ] Booking conversion rate
- [ ] Stripe webhook failures
- [ ] Database connection pool usage
- [ ] Redis cache hit rate
- [ ] Error rate by service

---

### PREP-095: Accessibility Audit & Fixes
**Priority**: P0 (Critical)
**Estimate**: 6 hours
**Labels**: frontend, accessibility, week-10

**Description:**
Audit and fix accessibility issues (WCAG 2.1 AA).

**Acceptance Criteria:**
- [ ] Run axe DevTools on all pages
- [ ] All forms have labels
- [ ] Color contrast ratio ≥4.5:1
- [ ] Keyboard navigation works
- [ ] Screen reader testing (VoiceOver/NVDA)
- [ ] Focus indicators visible
- [ ] ARIA labels on interactive elements

---

### PREP-096: Performance Optimization
**Priority**: P1 (High)
**Estimate**: 6 hours
**Labels**: frontend, performance, week-10

**Description:**
Optimize frontend performance for Lighthouse score ≥85.

**Acceptance Criteria:**
- [ ] Code splitting (React.lazy)
- [ ] Image optimization (WebP, lazy loading)
- [ ] Bundle size analysis (webpack-bundle-analyzer)
- [ ] Remove unused dependencies
- [ ] Enable gzip compression
- [ ] Lighthouse PWA score ≥85

---

### PREP-097: E2E Testing (Playwright)
**Priority**: P1 (High)
**Estimate**: 8 hours
**Labels**: testing, e2e, week-10

**Description:**
Create end-to-end tests for critical user journeys.

**Acceptance Criteria:**
- [ ] Test: Host creates listing → uploads photos → publishes
- [ ] Test: Renter searches → books kitchen → completes payment
- [ ] Test: Admin approves compliance documents
- [ ] Test: Reviews workflow
- [ ] Screenshot diffs tracked
- [ ] Run in CI on every PR

**Test Files:**
- `tests/e2e/host-flow.spec.ts`
- `tests/e2e/renter-flow.spec.ts`
- `tests/e2e/admin-flow.spec.ts`

---

### PREP-098: Security Hardening
**Priority**: P0 (Critical)
**Estimate**: 4 hours
**Labels**: security, backend, week-10

**Description:**
Apply security best practices and run security audit.

**Acceptance Criteria:**
- [ ] Helmet middleware configured (CSP, HSTS, etc.)
- [ ] Rate limiting on all endpoints
- [ ] Input sanitization (XSS prevention)
- [ ] SQL injection prevention (Prisma parameterized queries)
- [ ] CSRF protection
- [ ] npm audit clean
- [ ] Dependabot enabled

---

### PREP-099: Launch Checklist & Dry Run
**Priority**: P0 (Critical)
**Estimate**: 6 hours
**Labels**: launch, operations, week-10

**Description:**
Complete pre-launch checklist and dry run.

**Acceptance Criteria:**
- [ ] Seed 10 launch kitchens (production data)
- [ ] Create test renter accounts
- [ ] Complete end-to-end booking (production)
- [ ] Verify payout flow (use Stripe test mode transfer)
- [ ] Terms of Service live
- [ ] Privacy Policy live
- [ ] Support email configured
- [ ] On-call rotation defined
- [ ] Runbooks documented

**Launch Checklist:**
- [ ] All production secrets set
- [ ] DNS configured
- [ ] SSL certificates valid
- [ ] Monitoring alerts active
- [ ] Backup strategy verified
- [ ] Rollback plan documented

---

## Summary by Priority

### P0 (Critical) - Must Complete for MVP: 38 tickets
- Authentication: 5 tickets
- Listings: 5 tickets
- Compliance: 3 tickets
- Availability: 2 tickets
- Search: 2 tickets
- Booking & Payments: 8 tickets
- Stripe Connect: 2 tickets
- Reviews: 1 ticket
- Infrastructure: 10 tickets

### P1 (High) - Important but can ship without: 17 tickets
- Additional auth features
- Messaging
- Analytics
- Performance optimization

### Total: 55 tickets across 10 weeks
- Avg: 5-6 tickets per week
- Estimated total hours: 340 hours (8.5 weeks @ 40 hours/week)

---

## Ticket Management Best Practices

1. **Create tickets in your PM tool** (GitHub Issues, Linear, Jira)
2. **Assign estimates** based on your team's velocity
3. **Link PRs to tickets** for traceability
4. **Update ticket status** daily (To Do → In Progress → Review → Done)
5. **Hold standup** to unblock issues
6. **Track burndown chart** to monitor progress
7. **Adjust scope** if falling behind (move P1 tickets to post-MVP)

---

## GitHub Labels to Create

```
priority/p0-critical
priority/p1-high
priority/p2-medium

area/auth
area/listings
area/compliance
area/availability
area/search
area/booking
area/payments
area/messaging
area/reviews
area/admin
area/infrastructure
area/frontend
area/backend
area/testing

week/week-0
week/week-1
week/week-2
... (through week-10)

status/blocked
status/in-review
status/needs-design
```

---

## Next Steps

1. Import these tickets into your PM tool
2. Assign tickets to team members
3. Set sprint goals (1-week sprints)
4. Begin Week 0 infrastructure tasks
5. Track progress against 10-week timeline
