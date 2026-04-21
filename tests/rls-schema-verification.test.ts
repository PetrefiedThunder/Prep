import assert from 'node:assert'
import { describe, it, before } from 'node:test'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

/**
 * RLS Policy Verification Tests
 *
 * Parses supabase/schema.sql to verify that all expected RLS policies
 * are defined, all tables have RLS enabled, and DB constraints are correct.
 *
 * This is a static analysis test — it doesn't require a running Supabase
 * instance. It catches accidental policy removal or misconfiguration
 * during schema edits.
 */

let schema: string

before(() => {
  schema = readFileSync(join(import.meta.dirname, '..', 'supabase', 'schema.sql'), 'utf-8')
})

describe('RLS is enabled on all tables', () => {
  const tables = ['profiles', 'kitchens', 'kitchen_photos', 'stripe_accounts', 'bookings', 'payouts']

  for (const table of tables) {
    it(`${table} has RLS enabled`, () => {
      const pattern = new RegExp(`ALTER TABLE public\\.${table} ENABLE ROW LEVEL SECURITY`)
      assert.ok(pattern.test(schema), `RLS not enabled on ${table}`)
    })
  }
})

describe('Profiles RLS policies', () => {
  it('has SELECT policy scoped to own profile', () => {
    assert.ok(schema.includes('Users can view own profile'))
    assert.ok(schema.includes('ON public.profiles FOR SELECT'))
  })

  it('has UPDATE policy scoped to own profile', () => {
    assert.ok(schema.includes('Users can update own profile'))
    assert.ok(schema.includes('ON public.profiles FOR UPDATE'))
  })

  it('has INSERT policy scoped to own profile', () => {
    assert.ok(schema.includes('Users can insert own profile'))
    assert.ok(schema.includes('ON public.profiles FOR INSERT'))
  })

  it('uses auth.uid() = id for all profile policies', () => {
    // Count occurrences of auth.uid() = id in the profiles section
    const profileSection = schema.split('KITCHENS TABLE')[0]
    const matches = profileSection.match(/auth\.uid\(\) = id/g)
    assert.ok(matches && matches.length >= 3, 'Expected at least 3 auth.uid() = id checks for profiles')
  })
})

describe('Kitchens RLS policies', () => {
  it('allows anyone to view active kitchens', () => {
    assert.ok(schema.includes('Anyone can view active kitchens'))
    assert.ok(schema.includes('is_active = true'))
  })

  it('allows owners to view own kitchens (including inactive)', () => {
    assert.ok(schema.includes('Owners can view own kitchens'))
  })

  it('allows owners to insert own kitchens', () => {
    assert.ok(schema.includes('Owners can insert own kitchens'))
  })

  it('allows owners to update own kitchens', () => {
    assert.ok(schema.includes('Owners can update own kitchens'))
  })

  it('allows owners to delete own kitchens', () => {
    assert.ok(schema.includes('Owners can delete own kitchens'))
  })

  it('owner policies use auth.uid() = owner_id', () => {
    const kitchenSection = schema.split('KITCHENS TABLE')[1].split('KITCHEN_PHOTOS TABLE')[0]
    const matches = kitchenSection.match(/auth\.uid\(\) = owner_id/g)
    assert.ok(matches && matches.length >= 4, 'Expected at least 4 owner_id checks for kitchen policies')
  })
})

describe('Kitchen Photos RLS policies', () => {
  it('allows viewing photos of active kitchens only', () => {
    assert.ok(schema.includes('Anyone can view photos of active kitchens'))
  })

  it('restricts photo INSERT to kitchen owners', () => {
    assert.ok(schema.includes('Kitchen owners can insert photos'))
  })

  it('restricts photo UPDATE to kitchen owners', () => {
    assert.ok(schema.includes('Kitchen owners can update photos'))
  })

  it('restricts photo DELETE to kitchen owners', () => {
    assert.ok(schema.includes('Kitchen owners can delete photos'))
  })

  it('photo policies use subquery to check kitchen ownership', () => {
    const photoSection = schema.split('KITCHEN_PHOTOS TABLE')[1].split('STRIPE_ACCOUNTS TABLE')[0]
    const subqueries = photoSection.match(/SELECT 1 FROM public\.kitchens/g)
    assert.ok(subqueries && subqueries.length >= 3, 'Expected subquery ownership checks for photo policies')
  })
})

describe('Stripe Accounts RLS policies', () => {
  it('allows users to view own stripe account', () => {
    assert.ok(schema.includes('Users can view own stripe account'))
  })

  it('allows users to insert own stripe account', () => {
    assert.ok(schema.includes('Users can insert own stripe account'))
  })

  it('allows users to update own stripe account', () => {
    assert.ok(schema.includes('Users can update own stripe account'))
  })

  it('does NOT have a DELETE policy (accounts should persist)', () => {
    const stripeSection = schema.split('STRIPE_ACCOUNTS TABLE')[1].split('BOOKINGS TABLE')[0]
    assert.ok(!stripeSection.includes('FOR DELETE'), 'Stripe accounts should not have a DELETE policy')
  })
})

describe('Bookings RLS policies', () => {
  it('allows renters to view own bookings', () => {
    assert.ok(schema.includes('Renters can view own bookings'))
  })

  it('allows kitchen owners to view bookings for their kitchens', () => {
    assert.ok(schema.includes('Kitchen owners can view bookings for their kitchens'))
  })

  it('restricts booking creation to the renter (auth.uid() = renter_id)', () => {
    assert.ok(schema.includes('Users can create bookings'))
    const bookingSection = schema.split('BOOKINGS TABLE')[1].split('PAYOUTS TABLE')[0]
    assert.ok(bookingSection.includes('auth.uid() = renter_id'))
  })

  it('allows renters to update own bookings', () => {
    assert.ok(schema.includes('Renters can update own bookings'))
  })

  it('does NOT have a DELETE policy (bookings should be cancelled, not deleted)', () => {
    const bookingSection = schema.split('BOOKINGS TABLE')[1].split('PAYOUTS TABLE')[0]
    assert.ok(!bookingSection.includes('FOR DELETE'), 'Bookings should not have a DELETE policy')
  })
})

describe('Payouts RLS policies', () => {
  it('allows owners to view own payouts', () => {
    assert.ok(schema.includes('Owners can view own payouts'))
  })

  it('does NOT allow INSERT via RLS (webhook uses service role)', () => {
    const payoutSection = schema.split('PAYOUTS TABLE')[1].split('FUNCTIONS')[0]
    assert.ok(!payoutSection.includes('FOR INSERT'), 'Payouts should only be created by the webhook (service role)')
  })

  it('does NOT allow UPDATE via RLS (admin only)', () => {
    const payoutSection = schema.split('PAYOUTS TABLE')[1].split('FUNCTIONS')[0]
    assert.ok(!payoutSection.includes('FOR UPDATE'), 'Payouts should not be updatable by users')
  })

  it('does NOT allow DELETE via RLS', () => {
    const payoutSection = schema.split('PAYOUTS TABLE')[1].split('FUNCTIONS')[0]
    assert.ok(!payoutSection.includes('FOR DELETE'), 'Payouts should not be deletable')
  })
})

describe('Database constraints', () => {
  it('price_per_hour must be >= 0', () => {
    assert.ok(schema.includes('CHECK (price_per_hour >= 0)'))
  })

  it('max_capacity must be > 0', () => {
    assert.ok(schema.includes('CHECK (max_capacity > 0)'))
  })

  it('total_hours must be > 0', () => {
    assert.ok(schema.includes('CHECK (total_hours > 0)'))
  })

  it('total_amount must be >= 0', () => {
    assert.ok(schema.includes('CHECK (total_amount >= 0)'))
  })

  it('payout amount must be >= 0', () => {
    assert.ok(schema.includes('CHECK (amount >= 0)'))
  })

  it('platform_fee must be >= 0', () => {
    assert.ok(schema.includes('CHECK (platform_fee >= 0)'))
  })

  it('net_amount must be >= 0', () => {
    assert.ok(schema.includes('CHECK (net_amount >= 0)'))
  })

  it('booking end_time must be after start_time', () => {
    assert.ok(schema.includes('CONSTRAINT valid_time_range CHECK (end_time > start_time)'))
  })

  it('stripe_account_id is UNIQUE', () => {
    assert.ok(schema.includes('stripe_account_id TEXT UNIQUE NOT NULL'))
  })

  it('stripe_accounts user_id is UNIQUE (one account per user)', () => {
    const match = schema.match(/user_id UUID.*UNIQUE NOT NULL/)
    assert.ok(match, 'user_id should be UNIQUE on stripe_accounts')
  })

  it('payout booking_id is UNIQUE (one payout per booking)', () => {
    // In payouts table
    const payoutSection = schema.split('PAYOUTS TABLE')[1].split('FUNCTIONS')[0]
    assert.ok(payoutSection.includes('UNIQUE NOT NULL'), 'booking_id should be UNIQUE on payouts')
  })
})

describe('Critical indexes exist', () => {
  const expectedIndexes = [
    'idx_kitchens_owner_id',
    'idx_kitchens_city',
    'idx_kitchens_is_active',
    'idx_kitchen_photos_kitchen_id',
    'idx_stripe_accounts_user_id',
    'idx_stripe_accounts_stripe_id',
    'idx_bookings_kitchen_id',
    'idx_bookings_renter_id',
    'idx_bookings_start_time',
    'idx_bookings_status',
    'idx_payouts_booking_id',
    'idx_payouts_owner_id',
    'idx_payouts_status',
  ]

  for (const idx of expectedIndexes) {
    it(`index ${idx} exists`, () => {
      assert.ok(schema.includes(idx), `Missing index: ${idx}`)
    })
  }
})
