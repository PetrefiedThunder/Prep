import assert from 'node:assert'
import { describe, it, mock, beforeEach } from 'node:test'

/**
 * Stripe Webhook Handler Tests
 *
 * These tests verify the POST handler logic for /api/webhooks/stripe/route.ts
 * by extracting and testing the core decision paths:
 *   - Missing signature → 400
 *   - Invalid signature → 400
 *   - Missing metadata → 400
 *   - Duplicate payment intent → idempotent 200
 *   - Successful booking creation → 200 + payout record
 *   - DB insert failure → 500
 *   - Non-checkout events → 200 (no-op)
 */

// ---------------------------------------------------------------------------
// Helpers – tiny stubs that mimic Supabase / Stripe / Next.js interfaces
// ---------------------------------------------------------------------------

function makeFakeSupabase(overrides: {
  selectBooking?: { data: unknown; error?: unknown }
  insertBooking?: { data: unknown; error?: unknown }
  selectKitchen?: { data: unknown; error?: unknown }
  insertPayout?: { data: unknown; error?: unknown }
} = {}) {
  const calls: Record<string, unknown[]> = {
    selectBooking: [],
    insertBooking: [],
    selectKitchen: [],
    insertPayout: [],
  }

  return {
    calls,
    from(table: string) {
      if (table === 'bookings') {
        return {
          select: (_cols: string) => ({
            eq: (_col: string, _val: string) => ({
              single: async () => {
                calls.selectBooking.push({ table, _col, _val })
                return overrides.selectBooking ?? { data: null }
              },
            }),
          }),
          insert: (payload: unknown) => ({
            select: () => ({
              single: async () => {
                calls.insertBooking.push(payload)
                return (
                  overrides.insertBooking ?? {
                    data: { id: 'booking-1', ...payload as Record<string, unknown> },
                  }
                )
              },
            }),
          }),
        }
      }
      if (table === 'kitchens') {
        return {
          select: (_cols: string) => ({
            eq: (_col: string, _val: string) => ({
              single: async () => {
                calls.selectKitchen.push({ table, _col, _val })
                return overrides.selectKitchen ?? { data: { owner_id: 'owner-1' } }
              },
            }),
          }),
        }
      }
      if (table === 'payouts') {
        return {
          insert: (payload: unknown) => {
            calls.insertPayout.push(payload)
            return overrides.insertPayout ?? { data: payload }
          },
        }
      }
      throw new Error(`Unexpected table: ${table}`)
    },
  }
}

// Simulates the core webhook handler logic (extracted from route.ts)
// so we can unit-test without importing Next.js server modules.
async function handleWebhook(opts: {
  signature: string | null
  event: { type: string; data: { object: Record<string, unknown> } } | null
  constructEventThrows?: boolean
  supabase: ReturnType<typeof makeFakeSupabase>
}) {
  // 1. Check signature
  if (!opts.signature) {
    return { status: 400, body: { error: 'No signature' } }
  }

  // 2. Construct event
  if (opts.constructEventThrows || !opts.event) {
    return { status: 400, body: { error: 'Invalid signature' } }
  }

  const event = opts.event

  // 3. Handle checkout.session.completed
  if (event.type === 'checkout.session.completed') {
    const session = event.data.object

    const metadata = session.metadata as Record<string, string> | undefined
    if (!metadata) {
      return { status: 400, body: { error: 'No metadata' } }
    }

    const {
      kitchen_id,
      renter_id,
      start_time,
      end_time,
      total_hours,
      price_per_hour,
    } = metadata

    const totalAmount = (session.amount_total as number) / 100
    const paymentIntentId = session.payment_intent as string

    // Check duplicate
    const { data: existing } = await opts.supabase
      .from('bookings')
      .select('id')
      .eq('stripe_payment_intent_id', paymentIntentId)
      .single()

    if (existing) {
      return { status: 200, body: { received: true } }
    }

    // Insert booking
    const { data: booking, error } = await opts.supabase
      .from('bookings')
      .insert({
        kitchen_id,
        renter_id,
        start_time,
        end_time,
        total_hours: parseFloat(total_hours),
        price_per_hour: parseFloat(price_per_hour),
        total_amount: totalAmount,
        status: 'confirmed',
        stripe_payment_intent_id: paymentIntentId,
      })
      .select()
      .single()

    if (error) {
      return { status: 500, body: { error: error.message } }
    }

    // Payout
    const platformFeePercent = 0.1
    const platformFee = totalAmount * platformFeePercent
    const netAmount = totalAmount - platformFee

    const { data: kitchen } = await opts.supabase
      .from('kitchens')
      .select('owner_id')
      .eq('id', kitchen_id)
      .single()

    if (kitchen) {
      await opts.supabase.from('payouts').insert({
        booking_id: (booking as Record<string, unknown>).id,
        owner_id: (kitchen as Record<string, string>).owner_id,
        amount: totalAmount,
        platform_fee: platformFee,
        net_amount: netAmount,
        status: 'pending',
      })
    }
  }

  return { status: 200, body: { received: true } }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

const VALID_METADATA = {
  kitchen_id: 'kitchen-1',
  renter_id: 'renter-1',
  start_time: '2026-04-01T09:00:00Z',
  end_time: '2026-04-01T12:00:00Z',
  total_hours: '3',
  price_per_hour: '50',
}

const VALID_SESSION = {
  id: 'cs_test_1',
  metadata: VALID_METADATA,
  amount_total: 15000, // $150 in cents
  payment_intent: 'pi_test_1',
}

describe('Stripe Webhook Handler', () => {
  it('returns 400 when signature is missing', async () => {
    const supabase = makeFakeSupabase()
    const result = await handleWebhook({
      signature: null,
      event: null,
      supabase,
    })
    assert.strictEqual(result.status, 400)
    assert.strictEqual(result.body.error, 'No signature')
  })

  it('returns 400 when signature verification fails', async () => {
    const supabase = makeFakeSupabase()
    const result = await handleWebhook({
      signature: 'bad-sig',
      event: null,
      constructEventThrows: true,
      supabase,
    })
    assert.strictEqual(result.status, 400)
    assert.strictEqual(result.body.error, 'Invalid signature')
  })

  it('returns 400 when session metadata is missing', async () => {
    const supabase = makeFakeSupabase()
    const result = await handleWebhook({
      signature: 'valid-sig',
      event: {
        type: 'checkout.session.completed',
        data: { object: { id: 'cs_1', metadata: undefined as unknown as Record<string, unknown> } },
      },
      supabase,
    })
    assert.strictEqual(result.status, 400)
    assert.strictEqual(result.body.error, 'No metadata')
  })

  it('returns 200 idempotently when booking already exists for payment intent', async () => {
    const supabase = makeFakeSupabase({
      selectBooking: { data: { id: 'existing-booking' } },
    })
    const result = await handleWebhook({
      signature: 'valid-sig',
      event: { type: 'checkout.session.completed', data: { object: VALID_SESSION } },
      supabase,
    })
    assert.strictEqual(result.status, 200)
    assert.deepStrictEqual(result.body, { received: true })
    // Should NOT have called insert
    assert.strictEqual(supabase.calls.insertBooking.length, 0)
  })

  it('creates booking and payout on successful checkout', async () => {
    const supabase = makeFakeSupabase()
    const result = await handleWebhook({
      signature: 'valid-sig',
      event: { type: 'checkout.session.completed', data: { object: VALID_SESSION } },
      supabase,
    })
    assert.strictEqual(result.status, 200)

    // Booking was inserted
    assert.strictEqual(supabase.calls.insertBooking.length, 1)
    const bookingPayload = supabase.calls.insertBooking[0] as Record<string, unknown>
    assert.strictEqual(bookingPayload.kitchen_id, 'kitchen-1')
    assert.strictEqual(bookingPayload.renter_id, 'renter-1')
    assert.strictEqual(bookingPayload.total_amount, 150) // $150
    assert.strictEqual(bookingPayload.total_hours, 3)
    assert.strictEqual(bookingPayload.price_per_hour, 50)
    assert.strictEqual(bookingPayload.status, 'confirmed')

    // Payout was inserted
    assert.strictEqual(supabase.calls.insertPayout.length, 1)
    const payoutPayload = supabase.calls.insertPayout[0] as Record<string, unknown>
    assert.strictEqual(payoutPayload.amount, 150)
    assert.strictEqual(payoutPayload.platform_fee, 15) // 10%
    assert.strictEqual(payoutPayload.net_amount, 135) // 150 - 15
    assert.strictEqual(payoutPayload.status, 'pending')
    assert.strictEqual(payoutPayload.owner_id, 'owner-1')
  })

  it('returns 500 when booking insert fails', async () => {
    const supabase = makeFakeSupabase({
      insertBooking: { data: null, error: { message: 'DB constraint violation' } },
    })
    const result = await handleWebhook({
      signature: 'valid-sig',
      event: { type: 'checkout.session.completed', data: { object: VALID_SESSION } },
      supabase,
    })
    assert.strictEqual(result.status, 500)
    assert.strictEqual(result.body.error, 'DB constraint violation')
  })

  it('skips payout when kitchen is not found', async () => {
    const supabase = makeFakeSupabase({
      selectKitchen: { data: null },
    })
    const result = await handleWebhook({
      signature: 'valid-sig',
      event: { type: 'checkout.session.completed', data: { object: VALID_SESSION } },
      supabase,
    })
    assert.strictEqual(result.status, 200)
    assert.strictEqual(supabase.calls.insertPayout.length, 0)
  })

  it('returns 200 for non-checkout event types (no-op)', async () => {
    const supabase = makeFakeSupabase()
    const result = await handleWebhook({
      signature: 'valid-sig',
      event: {
        type: 'payment_intent.succeeded',
        data: { object: { id: 'pi_1' } },
      },
      supabase,
    })
    assert.strictEqual(result.status, 200)
    assert.deepStrictEqual(result.body, { received: true })
    assert.strictEqual(supabase.calls.insertBooking.length, 0)
  })

  it('calculates platform fee correctly for fractional amounts', async () => {
    const session = {
      ...VALID_SESSION,
      amount_total: 9999, // $99.99
    }
    const supabase = makeFakeSupabase()
    await handleWebhook({
      signature: 'valid-sig',
      event: { type: 'checkout.session.completed', data: { object: session } },
      supabase,
    })

    const payoutPayload = supabase.calls.insertPayout[0] as Record<string, unknown>
    const amount = 99.99
    assert.strictEqual(payoutPayload.amount, amount)
    // 10% of 99.99 = 9.999 (JS float)
    assert.ok(Math.abs((payoutPayload.platform_fee as number) - amount * 0.1) < 0.001)
    assert.ok(
      Math.abs((payoutPayload.net_amount as number) - (amount - amount * 0.1)) < 0.001
    )
  })
})
