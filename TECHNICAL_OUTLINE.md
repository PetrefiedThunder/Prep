# Prep Technical Outline (MVP v1.0)

Goal: Enable restaurants to rent out their certified commercial kitchens during off-hours to verified food entrepreneurs via a seamless, secure platform.

## 1. System Architecture Overview

Client (Web App / PWA / Admin Panel)
    ↕
API Gateway (Express/Node)
    ↕
Application Services (Authentication, Booking, Availability, Payments, Notifications)
    ↕
Database (PostgreSQL + Redis) + File Storage (S3 or Supabase Storage)
    ↕
Third-Party Integrations (Stripe, Plaid, Twilio, Google Maps, Yelp API, Health Department APIs)

## 2. Frontend (React + TailwindCSS)

### 2.1 Web App UI/UX
- Stack: React + Vite + TailwindCSS + Zustand for state management
- Views:
  - Landing Page
  - Kitchen Browser (Search, Filters: Time, Equipment, Certifications)
  - Kitchen Detail Page (Photos, Specs, Pricing, Calendar)
  - Booking Checkout Flow
  - User Dashboard (My Bookings, Messages, Payments)
  - Host Dashboard (Calendar, Listing Editor, Income)
  - Admin Panel (Moderation, Certification Verification)

### 2.2 PWA Enhancements
- Service Workers (for offline caching and push notifications)
- Add-to-home-screen support
- Responsive design for iOS/Android

## 3. Backend (Node.js + Express + PostgreSQL)

### 3.1 Core Services
- User Service: Auth, Profiles, KYC/Verification
- Kitchen Service: CRUD, Availability, Feature tags, Equipment
- Booking Service: Slot validation, conflict resolution, pricing
- Notification Service: Email/SMS, push (via Firebase Cloud Messaging)
- Review System: Ratings for renters and hosts

### 3.2 Middleware
- Auth middleware (JWT-based)
- Role-based access control (Admin, Host, Renter)
- Input validation (Zod / Joi)

### 3.3 APIs

RESTful endpoints with OpenAPI spec (in addition to existing integrations):

| Endpoint | Purpose | UI Coverage | Auth / Role Expectations |
| --- | --- | --- | --- |
| `GET /kitchens` | List kitchens with filter params for search and availability. | Kitchen Browser, Host Dashboard listing preview. | Public read, elevated rate limiting for unauthenticated requests. |
| `GET /kitchens/:id` | Retrieve full kitchen detail, amenities, pricing, calendar slots. | Kitchen Detail Page, Booking Checkout Flow. | Public read with sensitive host contact details hidden unless renter is authenticated. |
| `POST /kitchens` | Create a new kitchen listing and upload metadata. | Host Dashboard (Listing Editor). | Host-only (authenticated host role); requires completed verification checks. |
| `PUT /kitchens/:id` / `PATCH /kitchens/:id` | Update listing attributes, pricing, availability toggles. | Host Dashboard (Listing Editor). | Host-only for owned kitchen; admins may override for moderation. |
| `DELETE /kitchens/:id` | Soft delete or archive a listing. | Host Dashboard (Listing Management), Admin Panel moderation tools. | Host-only for owned kitchen; admin override for removals. |
| `GET /bookings` | List bookings with role-aware filtering (host sees their kitchens, renters see their reservations). | User Dashboard (My Bookings), Host Dashboard (Calendar view). | Auth required; renter sees own bookings, host sees bookings for owned kitchens, admins can view all. |
| `GET /bookings/:id` | Fetch detailed booking status, payment milestones, messaging thread IDs. | Booking Detail modal, Admin dispute resolution view. | Auth required; renter/host participants only, admin full access. |
| `POST /bookings` | Create booking requests with conflict validation and payment intent creation. | Booking Checkout Flow. | Authenticated renter role; host receives notification. |
| `GET /dashboards/host` | Aggregate metrics and upcoming reservations for hosts. | Host Dashboard home. | Host-only; blocks renter/admin access. |
| `GET /dashboards/renter` | Summaries of active bookings, recommendations, tasks. | User Dashboard landing. | Renter-only. |
| `GET /dashboards/admin` | Platform-wide KPIs, certification backlog, dispute counts. | Admin Panel analytics. | Admin-only; enforce MFA per RBAC policy. |
| `GET /admin/kitchens` | Moderation queue for new/flagged listings, certification status checks. | Admin Panel (Moderation). | Admin-only; includes elevated audit logging. |
| `POST /verify-health-cert` | Submit health certification documents for verification. | Host Dashboard (Compliance Upload). | Host-only; admin can review via moderation queue. |
| `POST /payment-intent` | Initiate payment capture prior to booking confirmation. | Booking Checkout Flow. | Authenticated renter; host/admin read-only visibility to status. |
| `POST /messages` | Send direct messages between renter and host. | User Dashboard messaging, Host Dashboard inbox. | Authenticated renters/hosts involved in booking; admin can monitor for disputes. |

## 4. Database Design (PostgreSQL + Redis)

### 4.1 Core Tables
- `users` (id, name, email, role, verified, created_at)
- `kitchens` (id, name, host_id, address, cert_level, photos, pricing)
- `bookings` (id, user_id, kitchen_id, start_time, end_time, status)
- `messages` (sender_id, recipient_id, body, timestamp)
- `reviews` (kitchen_id, user_id, rating, comment)
- `health_certifications` (kitchen_id, type, status, uploaded_at)
- `equipment` (kitchen_id, tag)
- `notifications` (user_id, type, body, read)

### 4.2 Redis (optional for MVP)
- Session store
- Booking availability cache

## 5. Payments + Identity Verification

### 5.1 Stripe Integration
- Connect accounts for hosts
- Instant payout to verified hosts
- Escrow system until booking is complete

### 5.2 Identity / Compliance
- Stripe Identity or Persona for KYC
- Health certificate document upload and admin moderation
- Optional: integrate Yelp or Google Business to pull reputation data

## 6. Authentication & Security
- JWT Auth (access/refresh tokens)
- bcrypt password hashing
- CORS + HTTPS enforcement
- Email verification (SendGrid)
- Admin roles with access gates
- GDPR-compliant data storage policies

## 7. AI/ML (Optional for v1, Roadmap for v2)
- NLP Matching Engine: match food entrepreneurs with ideal kitchens
- Pricing intelligence engine: suggest optimal hourly rates
- Auto-flag health cert documents for manual review
- Predictive availability: forecast demand based on cuisine, region

## 8. DevOps / CI/CD

### 8.1 Deployment
- Vercel/Netlify for frontend
- Fly.io / Railway / Render / Supabase for backend
- Docker containers for local dev + future scale
- PostgreSQL managed (Supabase / Neon / PlanetScale)

### 8.2 Environment Management
- `.env` for dev
- `.env.production` via secrets manager (e.g., Doppler, Vercel secrets)

### 8.3 Monitoring / Logging
- Logtail or Sentry for error tracking
- Cron jobs for booking cleanup & payouts
- Uptime monitoring (StatusCake or Upptime)

## 9. Testing

### 9.1 Frontend
- Playwright or Cypress for E2E testing
- Jest + React Testing Library for unit testing

### 9.2 Backend
- Jest + Supertest for route testing
- Faker.js or test fixtures for mock data

## 10. API Integrations & Regulatory Infrastructure
- Health Department APIs (document uploads or scraping for LA/NY)
- Geolocation: Google Places API for address verification
- Scheduling: Google Calendar sync (optional)
- Insurance Verification: CoverWallet API (optional)

## 11. Admin Control Panel
- View/Approve certifications
- Manage user disputes
- Ban/flag abusive users
- Metrics: total hours rented, earnings, utilization

## 12. Analytics
- Heap/LogRocket or PostHog for in-app user behavior
- Stripe Analytics for revenue tracking
- Admin dashboard with:
  - Most booked kitchens
  - Time-based trends
  - Certification status heatmap

## 13. Scalability & Roadmap Considerations

| Phase | Focus | Milestone |
|-------|-------|-----------|
| MVP | Listings, Booking, Payments | Launch with 10 kitchens |
| v1.1 | Push Notifications, Reviews | Grow to 50 kitchens |
| v1.5 | Smart Matching, Yelp Ratings | 3-city expansion |
| v2.0 | Native Apps, Kitchen Cam API | 1,000+ kitchens |

