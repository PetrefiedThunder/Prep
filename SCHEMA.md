# PrepChef Database Schema

This document describes the database schema for the PrepChef marketplace platform.

## Overview

The PrepChef schema is designed as a lean, focused database for a two-sided marketplace connecting kitchen owners with renters. All tables use Supabase Row Level Security (RLS) to ensure data isolation and security.

## Tables

### profiles

Extends Supabase `auth.users` with additional user information.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | References `auth.users.id` |
| email | TEXT | User's email (unique) |
| full_name | TEXT | User's full name (optional) |
| phone | TEXT | Contact phone number (optional) |
| created_at | TIMESTAMPTZ | Account creation timestamp |
| updated_at | TIMESTAMPTZ | Last update timestamp |

**Indexes:**
- Primary key on `id`
- Unique constraint on `email`

**RLS Policies:**
- Users can view, insert, and update their own profile only

**Notes:**
- Automatically created via trigger when a user signs up
- Links auth.users to application data

---

### kitchens

Commercial kitchen listings created by owners.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Kitchen identifier |
| owner_id | UUID (FK) | References `profiles.id` |
| title | TEXT | Kitchen listing title |
| description | TEXT | Detailed description |
| address | TEXT | Street address |
| city | TEXT | City name |
| state | TEXT | State/province |
| zip_code | TEXT | ZIP/postal code |
| price_per_hour | DECIMAL(10,2) | Hourly rental rate |
| max_capacity | INTEGER | Maximum occupancy |
| square_feet | INTEGER | Kitchen size (optional) |
| is_active | BOOLEAN | Listing visibility |
| created_at | TIMESTAMPTZ | Creation timestamp |
| updated_at | TIMESTAMPTZ | Last update timestamp |

**Indexes:**
- Primary key on `id`
- Index on `owner_id` (foreign key)
- Index on `city` (search optimization)
- Index on `is_active` (filtering)

**RLS Policies:**
- Anyone can view active kitchens (`is_active = true`)
- Owners can view all their own kitchens
- Owners can insert, update, and delete their own kitchens
- Cascade delete when owner profile is deleted

**Notes:**
- `price_per_hour` must be >= 0
- `max_capacity` must be > 0 if set
- Set `is_active = false` to hide from search without deleting

---

### kitchen_photos

Photos associated with kitchen listings.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Photo identifier |
| kitchen_id | UUID (FK) | References `kitchens.id` |
| url | TEXT | Photo URL (Supabase Storage or external) |
| is_primary | BOOLEAN | Primary listing photo |
| sort_order | INTEGER | Display order |
| created_at | TIMESTAMPTZ | Upload timestamp |

**Indexes:**
- Primary key on `id`
- Index on `kitchen_id` (foreign key)

**RLS Policies:**
- Anyone can view photos of active kitchens
- Kitchen owners can insert, update, and delete their kitchen photos
- Cascade delete when kitchen is deleted

**Notes:**
- Typically store photos in Supabase Storage and reference URLs here
- `is_primary = true` indicates the main listing photo
- `sort_order` controls gallery display order

---

### stripe_accounts

Stripe Connect account information for kitchen owners.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Record identifier |
| user_id | UUID (FK) | References `profiles.id` (unique) |
| stripe_account_id | TEXT | Stripe Connect account ID (unique) |
| onboarding_complete | BOOLEAN | Stripe onboarding status |
| created_at | TIMESTAMPTZ | Account creation timestamp |
| updated_at | TIMESTAMPTZ | Last update timestamp |

**Indexes:**
- Primary key on `id`
- Unique constraint on `user_id`
- Unique constraint on `stripe_account_id`
- Index on `user_id` (foreign key)
- Index on `stripe_account_id` (Stripe lookups)

**RLS Policies:**
- Users can view, insert, and update their own Stripe account only
- Cascade delete when user profile is deleted

**Notes:**
- One Stripe account per user
- `onboarding_complete` set to `true` after Stripe onboarding finishes
- Required before a kitchen owner can receive payouts

---

### bookings

Kitchen rental bookings made by renters.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Booking identifier |
| kitchen_id | UUID (FK) | References `kitchens.id` |
| renter_id | UUID (FK) | References `profiles.id` |
| start_time | TIMESTAMPTZ | Booking start time |
| end_time | TIMESTAMPTZ | Booking end time |
| total_hours | DECIMAL(10,2) | Duration in hours |
| price_per_hour | DECIMAL(10,2) | Rate at time of booking |
| total_amount | DECIMAL(10,2) | Total payment amount |
| status | booking_status | Booking status enum |
| stripe_payment_intent_id | TEXT | Stripe Payment Intent ID |
| created_at | TIMESTAMPTZ | Booking creation timestamp |
| updated_at | TIMESTAMPTZ | Last update timestamp |

**Booking Status Enum:**
- `pending` - Payment initiated but not confirmed
- `confirmed` - Payment successful, booking active
- `cancelled` - Booking cancelled
- `completed` - Booking finished

**Indexes:**
- Primary key on `id`
- Index on `kitchen_id` (foreign key)
- Index on `renter_id` (foreign key)
- Index on `start_time` (calendar queries)
- Index on `status` (filtering)

**RLS Policies:**
- Renters can view and update their own bookings
- Kitchen owners can view bookings for their kitchens
- Users can create bookings for themselves
- Cascade delete when kitchen or renter profile is deleted

**Constraints:**
- `end_time` must be greater than `start_time`
- `total_hours` must be > 0
- `price_per_hour` and `total_amount` must be >= 0

**Notes:**
- `price_per_hour` is snapshot at booking time (not a live reference)
- Created by Stripe webhook after successful payment
- `total_amount = total_hours * price_per_hour` (may include fees)

---

### payouts

Payouts to kitchen owners for completed bookings.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID (PK) | Payout identifier |
| booking_id | UUID (FK) | References `bookings.id` (unique) |
| owner_id | UUID (FK) | References `profiles.id` |
| amount | DECIMAL(10,2) | Gross booking amount |
| platform_fee | DECIMAL(10,2) | Platform fee deducted |
| net_amount | DECIMAL(10,2) | Amount transferred to owner |
| status | payout_status | Payout status enum |
| stripe_transfer_id | TEXT | Stripe Transfer ID |
| paid_at | TIMESTAMPTZ | Payout completion time |
| created_at | TIMESTAMPTZ | Record creation timestamp |
| updated_at | TIMESTAMPTZ | Last update timestamp |

**Payout Status Enum:**
- `pending` - Awaiting processing
- `processing` - Transfer initiated
- `paid` - Successfully transferred
- `failed` - Transfer failed

**Indexes:**
- Primary key on `id`
- Unique constraint on `booking_id` (one payout per booking)
- Index on `booking_id` (foreign key)
- Index on `owner_id` (foreign key)
- Index on `status` (filtering)

**RLS Policies:**
- Owners can view their own payouts only
- Cascade delete when booking or owner profile is deleted

**Constraints:**
- `amount`, `platform_fee`, and `net_amount` must be >= 0
- Typically `net_amount = amount - platform_fee`

**Notes:**
- Created after booking completion
- `paid_at` is set when transfer completes
- `stripe_transfer_id` references Stripe Connect transfer

---

## Functions and Triggers

### handle_new_user()

**Purpose:** Automatically create a profile entry when a new user signs up via Supabase Auth.

**Trigger:** `on_auth_user_created` (AFTER INSERT on `auth.users`)

**Behavior:**
- Creates a new row in `public.profiles` with the user's `id` and `email`
- Runs as `SECURITY DEFINER` to bypass RLS during creation

---

### update_updated_at_column()

**Purpose:** Automatically update the `updated_at` timestamp on row updates.

**Triggers:**
- `update_profiles_updated_at` (on `profiles`)
- `update_kitchens_updated_at` (on `kitchens`)
- `update_stripe_accounts_updated_at` (on `stripe_accounts`)
- `update_bookings_updated_at` (on `bookings`)
- `update_payouts_updated_at` (on `payouts`)

**Behavior:**
- Sets `updated_at = NOW()` before every UPDATE operation

---

## Row Level Security (RLS)

All tables have RLS enabled. Policies ensure:

1. **Data Isolation:** Users can only access their own data or publicly visible data
2. **Owner Control:** Kitchen owners control their listings and see their bookings
3. **Renter Privacy:** Renters can only see their own bookings
4. **Public Discovery:** Active kitchens are visible to all users for search

### Key RLS Patterns

- **Own Data Access:** `auth.uid() = <user_id_column>`
- **Kitchen Owner Access:** Subquery checking `kitchens.owner_id = auth.uid()`
- **Public Visibility:** `is_active = true` for kitchen listings

---

## Setup Instructions

1. **Create a Supabase project** at https://supabase.com
2. **Run the schema** by copying `supabase/schema.sql` into the Supabase SQL Editor
3. **Execute** the SQL to create all tables, indexes, policies, and triggers
4. **Update .env** with your Supabase project URL and keys

---

## Sample Queries

### Find active kitchens in a city

```sql
SELECT * FROM public.kitchens
WHERE city = 'San Francisco'
AND is_active = true
ORDER BY created_at DESC;
```

### Get a user's bookings with kitchen details

```sql
SELECT
  b.*,
  k.title AS kitchen_title,
  k.address,
  k.city
FROM public.bookings b
JOIN public.kitchens k ON b.kitchen_id = k.id
WHERE b.renter_id = auth.uid()
ORDER BY b.start_time DESC;
```

### Owner dashboard: Upcoming bookings for my kitchens

```sql
SELECT
  b.*,
  k.title AS kitchen_title,
  p.email AS renter_email
FROM public.bookings b
JOIN public.kitchens k ON b.kitchen_id = k.id
JOIN public.profiles p ON b.renter_id = p.id
WHERE k.owner_id = auth.uid()
AND b.start_time > NOW()
AND b.status = 'confirmed'
ORDER BY b.start_time ASC;
```

---

## Migration Strategy

For this lean MVP:
- All schema changes are applied via the single `supabase/schema.sql` file
- For production, consider using Supabase migrations CLI for versioned schema changes
- Always test schema changes in a development project first

---

## Notes and Considerations

1. **No Soft Deletes:** This schema uses hard deletes with cascade for simplicity. Add `deleted_at` columns if soft deletes are needed.

2. **Booking Conflicts:** The application layer should check for booking conflicts before creating a booking (no overlapping times for the same kitchen).

3. **Stripe Idempotency:** Use `stripe_payment_intent_id` to ensure bookings are not duplicated if webhooks retry.

4. **Platform Fees:** The `payouts.platform_fee` can be calculated as a percentage of the booking amount.

5. **Timezones:** All timestamps are stored as `TIMESTAMPTZ` (UTC). Convert to local timezone in the application layer.

6. **Search:** For more advanced search (geolocation, full-text), consider adding PostGIS or using Supabase's full-text search features.

7. **File Storage:** Kitchen photos should be stored in Supabase Storage, and the `kitchen_photos.url` field references the storage URL.

---

**Version:** 1.0
**Last Updated:** 2025-11-30
**Database:** PostgreSQL 15+ (Supabase)
