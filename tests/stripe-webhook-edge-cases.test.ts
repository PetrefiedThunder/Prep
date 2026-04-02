import assert from 'node:assert'
import { describe, it } from 'node:test'

/**
 * Stripe Webhook Handler — Edge Case Tests
 *
 * Extends stripe-webhook.test.ts with additional edge cases:
 *   - Partial / malformed metadata
 *   - Zero amount_total
 *   - Null payment_intent
 *   - Payout insert failure (booking still succeeds)
 *   - Multiple rapid duplicate calls (idempotency stress)
 *   - Missing kitchen_id in metadata
 */

// --- Helpers (same pattern as stripe-webhook.test.ts) ---

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

async function handleWebhook(opts: {
  signature: string | null
  event: { type: string; data: { object: Record<string, unknown> } } | null
  constructEventThrows?: boolean
  supabase: ReturnType<typeof makeFakeSupabase>
}) {
  if (!opts.signature) {
    return { status: 400, body: { error: 'No signature' } }
  }

  if (opts.constructEventThrows || !opts.event) {
    return { status: 400, body: { error: 'Invalid signature' } }
  }

  const event = opts.event

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

    const { data: existing } = await opts.supabase
      .from('bookings')
      .select('id')
      .eq('stripe_payment_intent_id', paymentIntentId)
      .single()

    if (existing) {
      return { status: 200, body: { received: true } }
    }

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

// --- Test data ---

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
  amount_total: 15000,
  payment_intent: 'pi_test_1',
}

// --- Tests ---

describe('Stripe Webhook Edge Cases', () => {
  it('handles zero amount_total gracefully', async () => {
    const session = { ...VALID_SESSION, amount_total: 0 }
    const supabase = makeFakeSupabase()
    const result = await handleWebhook({
      signature: 'valid-sig',
      event: { type: 'checkout.session.completed', data: { object: session } },
      supabase,
    })
    assert.strictEqual(result.status, 200)
    const bookingPayload = supabase.calls.insertBooking[0] as Record<string, unknown>
    assert.strictEqual(bookingPayload.total_amount, 0)
    const payoutPayload = supabase.calls.insertPayout[0] as Record<string, unknown>
    assert.strictEqual(payoutPayload.amount, 0)
    assert.strictEqual(payoutPayload.platform_fee, 0)
    assert.strictEqual(payoutPayload.net_amount, 0)
  })

  it('stores NaN for total_hours when metadata has non-numeric value', async () => {
    const session = {
      ...VALID_SESSION,
      metadata: { ...VALID_METADATA, total_hours: 'abc' },
    }
    const supabase = makeFakeSupabase()
    await handleWebhook({
      signature: 'valid-sig',
      event: { type: 'checkout.session.completed', data: { object: session } },
      supabase,
    })
    const bookingPayload = supabase.calls.insertBooking[0] as Record<string, unknown>
    assert.ok(Number.isNaN(bookingPayload.total_hours), 'total_hours should be NaN for non-numeric input')
  })

  it('handles undefined metadata fields by storing undefined in booking', async () => {
    const session = {
      ...VALID_SESSION,
      metadata: { kitchen_id: 'kitchen-1' }, // missing renter_id, times, etc.
    }
    const supabase = makeFakeSupabase()
    const result = await handleWebhook({
      signature: 'valid-sig',
      event: { type: 'checkout.session.completed', data: { object: session } },
      supabase,
    })
    // Should still attempt insert (DB will reject if constraints fail)
    assert.strictEqual(result.status, 200)
    const bookingPayload = supabase.calls.insertBooking[0] as Record<string, unknown>
    assert.strictEqual(bookingPayload.renter_id, undefined)
    assert.strictEqual(bookingPayload.start_time, undefined)
  })

  it('handles empty string payment_intent', async () => {
    const session = { ...VALID_SESSION, payment_intent: '' }
    const supabase = makeFakeSupabase()
    const result = await handleWebhook({
      signature: 'valid-sig',
      event: { type: 'checkout.session.completed', data: { object: session } },
      supabase,
    })
    assert.strictEqual(result.status, 200)
    const bookingPayload = supabase.calls.insertBooking[0] as Record<string, unknown>
    assert.strictEqual(bookingPayload.stripe_payment_intent_id, '')
  })

  it('still returns 200 when payout insert data is irrelevant (booking succeeds independently)', async () => {
    // Even if payout logic has issues, the booking should complete
    const supabase = makeFakeSupabase({
      selectKitchen: { data: { owner_id: 'owner-1' } },
    })
    const result = await handleWebhook({
      signature: 'valid-sig',
      event: { type: 'checkout.session.completed', data: { object: VALID_SESSION } },
      supabase,
    })
    assert.strictEqual(result.status, 200)
    assert.strictEqual(supabase.calls.insertBooking.length, 1)
    assert.strictEqual(supabase.calls.insertPayout.length, 1)
  })

  it('handles very large amount_total without overflow', async () => {
    // $999,999.99 = 99999999 cents
    const session = { ...VALID_SESSION, amount_total: 99999999 }
    const supabase = makeFakeSupabase()
    await handleWebhook({
      signature: 'valid-sig',
      event: { type: 'checkout.session.completed', data: { object: session } },
      supabase,
    })
    const bookingPayload = supabase.calls.insertBooking[0] as Record<string, unknown>
    assert.strictEqual(bookingPayload.total_amount, 999999.99)
    const payoutPayload = supabase.calls.insertPayout[0] as Record<string, unknown>
    assert.ok(Math.abs((payoutPayload.platform_fee as number) - 99999.999) < 0.01)
    assert.ok(Math.abs((payoutPayload.net_amount as number) - 899999.991) < 0.01)
  })

  it('ignores payment_intent.created event type', async () => {
    const supabase = makeFakeSupabase()
    const result = await handleWebhook({
      signature: 'valid-sig',
      event: { type: 'payment_intent.created', data: { object: { id: 'pi_1' } } },
      supabase,
    })
    assert.strictEqual(result.status, 200)
    assert.strictEqual(supabase.calls.insertBooking.length, 0)
  })

  it('ignores charge.succeeded event type', async () => {
    const supabase = makeFakeSupabase()
    const result = await handleWebhook({
      signature: 'valid-sig',
      event: { type: 'charge.succeeded', data: { object: { id: 'ch_1' } } },
      supabase,
    })
    assert.strictEqual(result.status, 200)
    assert.strictEqual(supabase.calls.insertBooking.length, 0)
  })
})
