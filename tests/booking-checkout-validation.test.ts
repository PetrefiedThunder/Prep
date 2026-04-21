import assert from 'node:assert'
import { describe, it } from 'node:test'

/**
 * Booking Checkout Session — Validation Logic Tests
 *
 * Tests the business rules in createCheckoutSession (lib/actions/bookings.ts):
 *   - Unauthorized user
 *   - Kitchen not found
 *   - Owner Stripe onboarding incomplete
 *   - Invalid booking times (end before start, zero hours)
 *   - Booking conflict detection
 *   - Amount calculation with platform fee
 */

// --- Mock Supabase (chainable query builder) ---

interface MockResult { data: unknown; error: unknown }

function mockChain(result: MockResult) {
  const chain: Record<string, unknown> = {}
  const methods = ['select', 'eq', 'in', 'lt', 'gt', 'single', 'order']
  for (const m of methods) {
    chain[m] = (..._args: unknown[]) => chain
  }
  chain.single = async () => result
  return chain
}

function makeMockSupabase(opts: {
  user: { id: string; email?: string } | null
  kitchen?: {
    id: string; price_per_hour: number; title: string;
    profiles?: { id: string };
    stripe_accounts?: { stripe_account_id: string; onboarding_complete: boolean } | null
  } | null
  kitchenError?: boolean
  conflictCount?: number
  conflictError?: boolean
}) {
  return {
    auth: {
      getUser: async () => ({ data: { user: opts.user } }),
    },
    from(table: string) {
      if (table === 'kitchens') {
        return {
          select: () => ({
            eq: (_col: string, _val: string) => ({
              single: async () => {
                if (opts.kitchenError) return { data: null, error: { message: 'Not found' } }
                return { data: opts.kitchen ?? null, error: opts.kitchen ? null : { message: 'Not found' } }
              },
            }),
          }),
        }
      }
      if (table === 'bookings') {
        return {
          select: (_cols: string, _opts?: unknown) => ({
            eq: (_col: string, _val: string) => ({
              in: (_col2: string, _val2: string[]) => ({
                lt: (_col3: string, _val3: string) => ({
                  gt: (_col4: string, _val4: string) => {
                    if (opts.conflictError) {
                      return Promise.resolve({ count: null, error: { message: 'Conflict check error' } })
                    }
                    return Promise.resolve({ count: opts.conflictCount ?? 0, error: null })
                  },
                }),
              }),
            }),
          }),
        }
      }
      throw new Error(`Unexpected table: ${table}`)
    },
  }
}

// Extracted logic from createCheckoutSession
async function validateCheckoutSession(
  supabase: ReturnType<typeof makeMockSupabase>,
  kitchenId: string,
  startTime: string,
  endTime: string
) {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { error: 'Unauthorized' }

  const { data: kitchen, error: kitchenError } = await supabase
    .from('kitchens')
    .select('*, profiles!kitchens_owner_id_fkey(id), stripe_accounts!stripe_accounts_user_id_fkey(stripe_account_id, onboarding_complete)')
    .eq('id', kitchenId)
    .single() as { data: typeof supabase extends { from: (t: string) => unknown } ? unknown : never; error: unknown }

  if (kitchenError || !kitchen) return { error: 'Kitchen not found' }

  const k = kitchen as {
    stripe_accounts: { stripe_account_id: string; onboarding_complete: boolean } | null
    price_per_hour: number
  }

  if (!k.stripe_accounts || !k.stripe_accounts.onboarding_complete) {
    return { error: 'Kitchen owner has not completed Stripe onboarding' }
  }

  const start = new Date(startTime)
  const end = new Date(endTime)
  const hours = (end.getTime() - start.getTime()) / (1000 * 60 * 60)

  if (hours <= 0) return { error: 'Invalid booking times' }

  // Conflict check
  try {
    const conflictResult = await supabase
      .from('bookings')
      .select('*', { count: 'exact', head: true })
      .eq('kitchen_id', kitchenId)
      .in('status', ['pending', 'confirmed'])
      .lt('start_time', end.toISOString())
      .gt('end_time', start.toISOString()) as unknown as { count: number | null; error: unknown }

    if (conflictResult.error) throw new Error('Failed to check booking availability')

    if (conflictResult.count !== null && conflictResult.count > 0) {
      return { error: 'This time slot is already booked. Please choose another time.' }
    }
  } catch (_e) {
    return { error: 'System error checking availability. Please try again.' }
  }

  const totalAmount = Math.round(hours * k.price_per_hour * 100)
  const platformFee = Math.round(totalAmount * 0.10)

  return { valid: true, totalAmount, platformFee, hours }
}

// --- Test data ---

const VALID_KITCHEN = {
  id: 'kitchen-1',
  price_per_hour: 50,
  title: 'Test Kitchen',
  profiles: { id: 'owner-1' },
  stripe_accounts: { stripe_account_id: 'acct_test', onboarding_complete: true },
}

describe('Checkout session validation', () => {
  it('returns Unauthorized when user is not logged in', async () => {
    const supabase = makeMockSupabase({ user: null, kitchen: VALID_KITCHEN })
    const result = await validateCheckoutSession(supabase, 'kitchen-1', '2026-04-01T09:00:00Z', '2026-04-01T12:00:00Z')
    assert.deepStrictEqual(result, { error: 'Unauthorized' })
  })

  it('returns error when kitchen is not found', async () => {
    const supabase = makeMockSupabase({ user: { id: 'user-1' }, kitchen: null, kitchenError: true })
    const result = await validateCheckoutSession(supabase, 'nonexistent', '2026-04-01T09:00:00Z', '2026-04-01T12:00:00Z')
    assert.deepStrictEqual(result, { error: 'Kitchen not found' })
  })

  it('returns error when owner has not completed Stripe onboarding', async () => {
    const kitchen = { ...VALID_KITCHEN, stripe_accounts: { stripe_account_id: 'acct_test', onboarding_complete: false } }
    const supabase = makeMockSupabase({ user: { id: 'user-1' }, kitchen })
    const result = await validateCheckoutSession(supabase, 'kitchen-1', '2026-04-01T09:00:00Z', '2026-04-01T12:00:00Z')
    assert.deepStrictEqual(result, { error: 'Kitchen owner has not completed Stripe onboarding' })
  })

  it('returns error when owner has no Stripe account at all', async () => {
    const kitchen = { ...VALID_KITCHEN, stripe_accounts: null }
    const supabase = makeMockSupabase({ user: { id: 'user-1' }, kitchen })
    const result = await validateCheckoutSession(supabase, 'kitchen-1', '2026-04-01T09:00:00Z', '2026-04-01T12:00:00Z')
    assert.deepStrictEqual(result, { error: 'Kitchen owner has not completed Stripe onboarding' })
  })

  it('returns error when end time is before start time', async () => {
    const supabase = makeMockSupabase({ user: { id: 'user-1' }, kitchen: VALID_KITCHEN })
    const result = await validateCheckoutSession(supabase, 'kitchen-1', '2026-04-01T12:00:00Z', '2026-04-01T09:00:00Z')
    assert.deepStrictEqual(result, { error: 'Invalid booking times' })
  })

  it('returns error when start and end time are the same (zero hours)', async () => {
    const supabase = makeMockSupabase({ user: { id: 'user-1' }, kitchen: VALID_KITCHEN })
    const result = await validateCheckoutSession(supabase, 'kitchen-1', '2026-04-01T09:00:00Z', '2026-04-01T09:00:00Z')
    assert.deepStrictEqual(result, { error: 'Invalid booking times' })
  })

  it('returns conflict error when time slot is already booked', async () => {
    const supabase = makeMockSupabase({ user: { id: 'user-1' }, kitchen: VALID_KITCHEN, conflictCount: 1 })
    const result = await validateCheckoutSession(supabase, 'kitchen-1', '2026-04-01T09:00:00Z', '2026-04-01T12:00:00Z')
    assert.deepStrictEqual(result, { error: 'This time slot is already booked. Please choose another time.' })
  })

  it('returns system error when conflict check fails', async () => {
    const supabase = makeMockSupabase({ user: { id: 'user-1' }, kitchen: VALID_KITCHEN, conflictError: true })
    const result = await validateCheckoutSession(supabase, 'kitchen-1', '2026-04-01T09:00:00Z', '2026-04-01T12:00:00Z')
    assert.deepStrictEqual(result, { error: 'System error checking availability. Please try again.' })
  })

  it('calculates correct amount for valid 3-hour booking at $50/hr', async () => {
    const supabase = makeMockSupabase({ user: { id: 'user-1' }, kitchen: VALID_KITCHEN })
    const result = await validateCheckoutSession(supabase, 'kitchen-1', '2026-04-01T09:00:00Z', '2026-04-01T12:00:00Z')
    assert.strictEqual((result as Record<string, unknown>).valid, true)
    assert.strictEqual((result as Record<string, unknown>).totalAmount, 15000) // $150 in cents
    assert.strictEqual((result as Record<string, unknown>).platformFee, 1500) // 10%
    assert.strictEqual((result as Record<string, unknown>).hours, 3)
  })

  it('calculates correct amount for fractional hours (1.5h at $40/hr)', async () => {
    const kitchen = { ...VALID_KITCHEN, price_per_hour: 40 }
    const supabase = makeMockSupabase({ user: { id: 'user-1' }, kitchen })
    const result = await validateCheckoutSession(supabase, 'kitchen-1', '2026-04-01T09:00:00Z', '2026-04-01T10:30:00Z')
    assert.strictEqual((result as Record<string, unknown>).valid, true)
    assert.strictEqual((result as Record<string, unknown>).totalAmount, 6000) // $60 in cents
    assert.strictEqual((result as Record<string, unknown>).platformFee, 600) // 10%
    assert.strictEqual((result as Record<string, unknown>).hours, 1.5)
  })

  it('handles multiple existing conflicts (count > 1)', async () => {
    const supabase = makeMockSupabase({ user: { id: 'user-1' }, kitchen: VALID_KITCHEN, conflictCount: 5 })
    const result = await validateCheckoutSession(supabase, 'kitchen-1', '2026-04-01T09:00:00Z', '2026-04-01T12:00:00Z')
    assert.deepStrictEqual(result, { error: 'This time slot is already booked. Please choose another time.' })
  })
})
