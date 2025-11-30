# API Documentation - PrepChef

This document describes the server actions and API routes in PrepChef.

## Overview

PrepChef uses:
- **Server Actions** for mutations (create, update, delete)
- **Direct Supabase queries** for reads in Server Components
- **API Routes** for webhooks and external integrations

All server actions and API routes respect Row Level Security (RLS) policies.

## Server Actions

Server actions are defined in `lib/actions/` and use the `'use server'` directive.

### Kitchen Actions (`lib/actions/kitchens.ts`)

#### `createKitchen(data: KitchenFormData)`

Creates a new kitchen listing.

**Parameters:**
```typescript
{
  title: string
  description: string
  address: string
  city: string
  state: string
  zip_code: string
  price_per_hour: number
  max_capacity: number
  square_feet?: number
}
```

**Returns:**
```typescript
{ data: Kitchen } | { error: string }
```

**Authorization:** Must be authenticated

**Example:**
```typescript
const result = await createKitchen({
  title: "Professional Commercial Kitchen",
  description: "Fully equipped kitchen in downtown SF",
  address: "123 Market St",
  city: "San Francisco",
  state: "CA",
  zip_code: "94102",
  price_per_hour: 50,
  max_capacity: 5,
  square_feet: 1000
})
```

---

#### `updateKitchen(id: string, data: KitchenFormData)`

Updates an existing kitchen listing.

**Authorization:** Must be the kitchen owner

**Returns:**
```typescript
{ data: Kitchen } | { error: string }
```

---

#### `toggleKitchenActive(id: string, isActive: boolean)`

Activates or deactivates a kitchen listing.

**Authorization:** Must be the kitchen owner

**Returns:**
```typescript
{ success: true } | { error: string }
```

---

#### `deleteKitchen(id: string)`

Permanently deletes a kitchen listing.

**Authorization:** Must be the kitchen owner

**Returns:**
```typescript
{ success: true } | { error: string }
```

**Note:** Cascade deletes all associated photos and bookings.

---

#### `getOwnerKitchens()`

Retrieves all kitchens for the authenticated owner.

**Authorization:** Must be authenticated

**Returns:**
```typescript
{ data: KitchenWithPhotos[] } | { error: string }
```

---

#### `getKitchen(id: string)`

Retrieves a single kitchen by ID with photos and owner info.

**Authorization:** None (public for active kitchens)

**Returns:**
```typescript
{ data: Kitchen & { kitchen_photos: KitchenPhoto[], profiles: Profile } } | { error: string }
```

---

### Stripe Actions (`lib/actions/stripe.ts`)

#### `createConnectAccount()`

Creates a Stripe Connect account for the authenticated user.

**Returns:**
```typescript
{
  accountId: string
  onboardingComplete: boolean
} | { error: string }
```

**Authorization:** Must be authenticated

---

#### `createAccountLink()`

Creates a Stripe account onboarding link.

**Returns:**
```typescript
{ url: string } | { error: string }
```

**Authorization:** Must be authenticated with existing Stripe account

---

#### `checkOnboardingStatus()`

Checks and updates Stripe Connect onboarding status.

**Returns:**
```typescript
{
  onboardingComplete: boolean
  accountId?: string
} | { error: string }
```

**Authorization:** Must be authenticated

---

### Booking Actions (`lib/actions/bookings.ts`)

#### `createCheckoutSession(kitchenId: string, startTime: string, endTime: string)`

Creates a Stripe Checkout Session for a kitchen booking.

**Parameters:**
- `kitchenId`: UUID of the kitchen
- `startTime`: ISO 8601 datetime string
- `endTime`: ISO 8601 datetime string

**Returns:**
```typescript
{ url: string } | { error: string }
```

**Authorization:** Must be authenticated

**Payment Flow:**
1. Validates kitchen exists and owner has completed Stripe onboarding
2. Calculates total amount based on hourly rate
3. Applies 10% platform fee
4. Creates Stripe Checkout Session with application fee
5. Returns checkout URL

**Example:**
```typescript
const result = await createCheckoutSession(
  'kitchen-uuid',
  '2024-12-01T10:00:00',
  '2024-12-01T14:00:00'
)

if (result.url) {
  window.location.href = result.url
}
```

---

#### `getUserBookings()`

Retrieves all bookings for the authenticated renter.

**Returns:**
```typescript
{ data: BookingWithKitchen[] } | { error: string }
```

**Authorization:** Must be authenticated

---

#### `getOwnerBookings()`

Retrieves all bookings for kitchens owned by the authenticated user.

**Returns:**
```typescript
{ data: BookingWithKitchen[] } | { error: string }
```

**Authorization:** Must be authenticated

---

## API Routes

### Stripe Webhook (`app/api/webhooks/stripe/route.ts`)

Handles Stripe webhook events.

**Endpoint:** `POST /api/webhooks/stripe`

**Authentication:** Stripe signature verification

**Supported Events:**
- `checkout.session.completed`

**Behavior:**
1. Verifies webhook signature
2. Extracts booking metadata from checkout session
3. Creates booking record in database (idempotent)
4. Creates payout record for kitchen owner
5. Returns `200 OK`

**Metadata Schema:**
```typescript
{
  kitchen_id: string
  renter_id: string
  start_time: string (ISO 8601)
  end_time: string (ISO 8601)
  total_hours: string
  price_per_hour: string
}
```

**Idempotency:**
- Uses `stripe_payment_intent_id` to prevent duplicate bookings
- Safe to retry on webhook failures

**Error Handling:**
- Returns `400` for invalid signatures
- Returns `500` for database errors
- Logs all errors for monitoring

---

## Direct Supabase Queries

Some pages query Supabase directly in Server Components for better performance.

### Kitchen Search (`app/kitchens/page.tsx`)

**Query:**
```typescript
supabase
  .from('kitchens')
  .select(`
    *,
    kitchen_photos (*)
  `)
  .eq('is_active', true)
  .ilike('city', `%${city}%`)
  .gte('price_per_hour', minPrice)
  .lte('price_per_hour', maxPrice)
  .order('created_at', { ascending: false })
  .limit(50)
```

**Filters:**
- `city` (case-insensitive partial match)
- `minPrice` (greater than or equal)
- `maxPrice` (less than or equal)

**Pagination:** Limited to 50 results (can be extended)

---

## Authentication

All authenticated requests use Supabase Auth via middleware.

### Middleware (`middleware.ts`)

- Runs on every request
- Refreshes auth session automatically
- Sets cookies for session management

### Protected Routes

Routes that require authentication redirect to `/auth/login`:
- `/owner/*` - Kitchen owner pages
- `/renter/*` - Renter pages
- `/profile` - User profile

### Row Level Security

All database tables have RLS enabled:

**Kitchens:**
- Anyone can view active kitchens
- Owners can view/edit/delete their own kitchens

**Bookings:**
- Renters can view their own bookings
- Kitchen owners can view bookings for their kitchens

**Stripe Accounts:**
- Users can only view/edit their own account

**Payouts:**
- Owners can only view their own payouts

---

## Error Handling

### Server Actions

All server actions return:
```typescript
{ data: T } | { error: string }
```

**Example Usage:**
```typescript
const result = await createKitchen(formData)

if (result.error) {
  setError(result.error)
} else {
  // Success
  router.push('/owner/kitchens')
}
```

### API Routes

API routes return standard HTTP status codes:
- `200` - Success
- `400` - Bad request (invalid input)
- `401` - Unauthorized
- `500` - Server error

---

## Rate Limiting

Currently no rate limiting is implemented. For production, consider:
- Vercel Edge Functions have built-in DDoS protection
- Add rate limiting middleware for expensive operations
- Use Supabase connection pooling

---

## Data Validation

### Client-Side
- HTML5 form validation
- React state validation

### Server-Side
- Supabase RLS policies
- TypeScript type checking
- Custom validation in server actions

### Database
- PostgreSQL constraints
- Foreign key relationships
- Check constraints (e.g., `price_per_hour >= 0`)

---

## Example Flows

### Complete Booking Flow

1. **User selects kitchen and date/time**
   - Frontend form at `/kitchens/[id]/book`

2. **Create checkout session**
   ```typescript
   const result = await createCheckoutSession(
     kitchenId,
     startDateTime,
     endDateTime
   )
   ```

3. **Redirect to Stripe Checkout**
   ```typescript
   window.location.href = result.url
   ```

4. **User completes payment**
   - Stripe processes payment
   - Stripe sends webhook to `/api/webhooks/stripe`

5. **Webhook creates booking**
   ```typescript
   await supabase.from('bookings').insert({
     kitchen_id,
     renter_id,
     start_time,
     end_time,
     total_amount,
     status: 'confirmed',
     stripe_payment_intent_id
   })
   ```

6. **User redirected to success page**
   - Displays at `/bookings/success`

7. **Booking appears in dashboards**
   - Owner: `/owner/bookings`
   - Renter: `/renter/bookings`

---

## Testing

### Test Mode (Development)

Use Stripe test cards:
- Success: `4242 4242 4242 4242`
- Declined: `4000 0000 0000 0002`

Webhook testing with Stripe CLI:
```bash
stripe listen --forward-to localhost:3000/api/webhooks/stripe
```

### Production Testing

- Use small real payments
- Monitor Stripe Dashboard
- Check Vercel logs for webhook delivery

---

## Performance Considerations

### Caching
- Static pages cached by Vercel CDN
- Dynamic pages rendered on-demand
- Database queries use Supabase connection pooling

### Optimization
- Server Components for data fetching
- Client Components only where interactivity is needed
- Minimal JavaScript bundle size

### Monitoring
- Vercel Analytics for performance
- Supabase Dashboard for query performance
- Stripe Dashboard for payment metrics

---

For more details on the database schema, see [SCHEMA.md](./SCHEMA.md).
