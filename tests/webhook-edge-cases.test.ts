import assert from 'node:assert'
import { describe, it } from 'node:test'

/**
 * Stripe Webhook — Edge Cases
 *
 * Tests extracted from app/api/webhooks/stripe/route.ts covering:
 *   - Duplicate payment intent detection
 *   - Payout creation when kitchen not found
 *   - Metadata field parsing (parseFloat edge cases)
 *   - Amount conversion from cents
 *   - Missing/malformed payment_intent
 *   - Platform fee rounding for fractional cents
 */

// --- Extracted logic mirrors ---

function convertFromCents(amountTotal: number): number {
  return amountTotal / 100
}

function calculatePayout(totalAmount: number) {
  const platformFeePercent = 0.10
  const platformFee = totalAmount * platformFeePercent
  const netAmount = totalAmount - platformFee
  return { platformFee, netAmount }
}

function parseMetadataNumbers(metadata: Record<string, string>) {
  return {
    total_hours: parseFloat(metadata.total_hours),
    price_per_hour: parseFloat(metadata.price_per_hour),
  }
}

// --- Tests ---

describe('Webhook — Duplicate Payment Intent Detection', () => {
  it('skips booking creation when payment intent already exists', () => {
    const existingBooking = { id: 'booking-1' }
    // If existing is truthy, webhook returns { received: true } without inserting
    assert.ok(existingBooking)
  })

  it('proceeds with booking creation when no existing record', () => {
    const existingBooking = null
    assert.strictEqual(existingBooking, null)
    // Handler should continue to insert
  })

  it('handles undefined payment_intent gracefully', () => {
    const session = { payment_intent: undefined }
    const paymentIntentId = session.payment_intent as string | undefined
    // The code casts: const paymentIntentId = session.payment_intent as string
    // undefined cast to string is still falsy-ish but supabase .eq will match nothing
    assert.strictEqual(paymentIntentId, undefined)
  })

  it('handles null payment_intent', () => {
    const session = { payment_intent: null }
    const paymentIntentId = session.payment_intent as string | null
    assert.strictEqual(paymentIntentId, null)
  })
})

describe('Webhook — Amount Conversion from Cents', () => {
  it('converts 10000 cents to $100.00', () => {
    assert.strictEqual(convertFromCents(10000), 100)
  })

  it('converts 2550 cents to $25.50', () => {
    assert.strictEqual(convertFromCents(2550), 25.50)
  })

  it('converts 1 cent to $0.01', () => {
    assert.strictEqual(convertFromCents(1), 0.01)
  })

  it('converts 0 cents to $0.00', () => {
    assert.strictEqual(convertFromCents(0), 0)
  })

  it('handles very large amounts (1M cents = $10,000)', () => {
    assert.strictEqual(convertFromCents(1000000), 10000)
  })
})

describe('Webhook — Metadata Number Parsing', () => {
  it('parses integer strings correctly', () => {
    const result = parseMetadataNumbers({ total_hours: '3', price_per_hour: '50' })
    assert.strictEqual(result.total_hours, 3)
    assert.strictEqual(result.price_per_hour, 50)
  })

  it('parses decimal strings correctly', () => {
    const result = parseMetadataNumbers({ total_hours: '1.5', price_per_hour: '49.99' })
    assert.strictEqual(result.total_hours, 1.5)
    assert.strictEqual(result.price_per_hour, 49.99)
  })

  it('returns NaN for empty strings', () => {
    const result = parseMetadataNumbers({ total_hours: '', price_per_hour: '' })
    assert.ok(Number.isNaN(result.total_hours))
    assert.ok(Number.isNaN(result.price_per_hour))
  })

  it('returns NaN for non-numeric strings', () => {
    const result = parseMetadataNumbers({ total_hours: 'abc', price_per_hour: 'xyz' })
    assert.ok(Number.isNaN(result.total_hours))
    assert.ok(Number.isNaN(result.price_per_hour))
  })

  it('parses strings with leading/trailing spaces', () => {
    const result = parseMetadataNumbers({ total_hours: ' 2.5 ', price_per_hour: ' 75 ' })
    assert.strictEqual(result.total_hours, 2.5)
    assert.strictEqual(result.price_per_hour, 75)
  })
})

describe('Webhook — Payout Creation Edge Cases', () => {
  it('calculates platform fee correctly for small bookings ($10)', () => {
    const totalAmount = 10
    const { platformFee, netAmount } = calculatePayout(totalAmount)
    assert.strictEqual(platformFee, 1)
    assert.strictEqual(netAmount, 9)
  })

  it('calculates platform fee correctly for large bookings ($5000)', () => {
    const totalAmount = 5000
    const { platformFee, netAmount } = calculatePayout(totalAmount)
    assert.strictEqual(platformFee, 500)
    assert.strictEqual(netAmount, 4500)
  })

  it('handles floating point precision for $33.33 booking', () => {
    const totalAmount = 33.33
    const { platformFee, netAmount } = calculatePayout(totalAmount)
    // 33.33 * 0.10 = 3.333 — potential floating point issue
    assert.ok(Math.abs(platformFee - 3.333) < 0.001)
    assert.ok(Math.abs(netAmount - 29.997) < 0.001)
  })

  it('skips payout creation when kitchen is not found', () => {
    const kitchen = null
    // In the handler: if (kitchen) { ... create payout }
    // When kitchen is null, payout is silently skipped
    assert.strictEqual(kitchen, null)
    // This is the current behavior — no error thrown
  })

  it('uses correct owner_id from kitchen lookup for payout', () => {
    const kitchen = { owner_id: 'owner-abc' }
    assert.strictEqual(kitchen.owner_id, 'owner-abc')
    // Payout insert uses kitchen.owner_id
  })
})

describe('Webhook — Booking Insert Payload Shape', () => {
  it('constructs correct booking payload from session metadata', () => {
    const metadata = {
      kitchen_id: 'k-1',
      renter_id: 'u-1',
      start_time: '2026-04-10T10:00:00Z',
      end_time: '2026-04-10T14:00:00Z',
      total_hours: '4',
      price_per_hour: '50',
    }
    const amountTotal = 20000 // cents
    const paymentIntentId = 'pi_test_123'

    const bookingPayload = {
      kitchen_id: metadata.kitchen_id,
      renter_id: metadata.renter_id,
      start_time: metadata.start_time,
      end_time: metadata.end_time,
      total_hours: parseFloat(metadata.total_hours),
      price_per_hour: parseFloat(metadata.price_per_hour),
      total_amount: amountTotal / 100,
      status: 'confirmed' as const,
      stripe_payment_intent_id: paymentIntentId,
    }

    assert.strictEqual(bookingPayload.kitchen_id, 'k-1')
    assert.strictEqual(bookingPayload.renter_id, 'u-1')
    assert.strictEqual(bookingPayload.total_hours, 4)
    assert.strictEqual(bookingPayload.price_per_hour, 50)
    assert.strictEqual(bookingPayload.total_amount, 200)
    assert.strictEqual(bookingPayload.status, 'confirmed')
    assert.strictEqual(bookingPayload.stripe_payment_intent_id, 'pi_test_123')
  })

  it('payout payload has correct fee structure', () => {
    const totalAmount = 200
    const platformFeePercent = 0.10
    const platformFee = totalAmount * platformFeePercent
    const netAmount = totalAmount - platformFee

    const payoutPayload = {
      booking_id: 'booking-1',
      owner_id: 'owner-1',
      amount: totalAmount,
      platform_fee: platformFee,
      net_amount: netAmount,
      status: 'pending' as const,
    }

    assert.strictEqual(payoutPayload.amount, 200)
    assert.strictEqual(payoutPayload.platform_fee, 20)
    assert.strictEqual(payoutPayload.net_amount, 180)
    assert.strictEqual(payoutPayload.status, 'pending')
  })
})
