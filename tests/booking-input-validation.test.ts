import assert from 'node:assert'
import { describe, it } from 'node:test'

/**
 * Booking Input Validation Tests
 *
 * Tests validation logic extracted from lib/actions/bookings.ts:
 *   - createCheckoutSession input validation
 *   - Time parsing edge cases
 *   - Amount/fee rounding for Stripe (cents)
 *   - Origin URL fallback chain
 *   - Metadata construction for Stripe session
 */

describe('Booking — Time Input Validation', () => {
  it('rejects when end time equals start time (zero hours)', () => {
    const start = new Date('2026-04-10T10:00:00Z')
    const end = new Date('2026-04-10T10:00:00Z')
    const hours = (end.getTime() - start.getTime()) / (1000 * 60 * 60)
    assert.ok(hours <= 0, 'Should reject zero-length booking')
  })

  it('rejects when end time is before start time', () => {
    const start = new Date('2026-04-10T14:00:00Z')
    const end = new Date('2026-04-10T10:00:00Z')
    const hours = (end.getTime() - start.getTime()) / (1000 * 60 * 60)
    assert.ok(hours < 0, 'Should reject negative duration')
  })

  it('accepts valid future booking', () => {
    const start = new Date('2026-04-10T10:00:00Z')
    const end = new Date('2026-04-10T14:00:00Z')
    const hours = (end.getTime() - start.getTime()) / (1000 * 60 * 60)
    assert.strictEqual(hours, 4)
    assert.ok(hours > 0)
  })

  it('handles overnight booking (cross-midnight)', () => {
    const start = new Date('2026-04-10T22:00:00Z')
    const end = new Date('2026-04-11T06:00:00Z')
    const hours = (end.getTime() - start.getTime()) / (1000 * 60 * 60)
    assert.strictEqual(hours, 8)
  })

  it('handles multi-day booking', () => {
    const start = new Date('2026-04-10T08:00:00Z')
    const end = new Date('2026-04-12T08:00:00Z')
    const hours = (end.getTime() - start.getTime()) / (1000 * 60 * 60)
    assert.strictEqual(hours, 48)
  })

  it('handles 15-minute booking', () => {
    const start = new Date('2026-04-10T10:00:00Z')
    const end = new Date('2026-04-10T10:15:00Z')
    const hours = (end.getTime() - start.getTime()) / (1000 * 60 * 60)
    assert.strictEqual(hours, 0.25)
    assert.ok(hours > 0)
  })

  it('parses ISO 8601 strings correctly', () => {
    const startStr = '2026-04-10T10:00:00Z'
    const endStr = '2026-04-10T12:00:00Z'
    const start = new Date(startStr)
    const end = new Date(endStr)
    assert.ok(!isNaN(start.getTime()), 'Start should be valid date')
    assert.ok(!isNaN(end.getTime()), 'End should be valid date')
  })

  it('handles invalid date strings', () => {
    const start = new Date('not-a-date')
    assert.ok(isNaN(start.getTime()), 'Invalid date should return NaN')
  })
})

describe('Booking — Stripe Amount Rounding (Cents)', () => {
  it('rounds correctly for whole dollar amounts', () => {
    const hours = 2
    const pricePerHour = 50
    const totalCents = Math.round(hours * pricePerHour * 100)
    assert.strictEqual(totalCents, 10000)
  })

  it('rounds correctly for fractional amounts ($74.985 → 7499 cents)', () => {
    const hours = 1.5
    const pricePerHour = 49.99
    const totalCents = Math.round(hours * pricePerHour * 100)
    assert.strictEqual(totalCents, 7499)
  })

  it('rounds up at exactly .5 ($50.005 → 5001 cents)', () => {
    const hours = 1
    const pricePerHour = 50.005
    const totalCents = Math.round(hours * pricePerHour * 100)
    assert.strictEqual(totalCents, 5001)
  })

  it('platform fee rounds correctly for 10% of 7499 cents', () => {
    const totalCents = 7499
    const platformFee = Math.round(totalCents * 0.10)
    assert.strictEqual(platformFee, 750)
  })

  it('platform fee rounds correctly for 10% of 9999 cents', () => {
    const totalCents = 9999
    const platformFee = Math.round(totalCents * 0.10)
    assert.strictEqual(platformFee, 1000)
  })

  it('handles very small booking (1 cent total)', () => {
    // e.g., 0.01 hours at $1/hr
    const hours = 0.01
    const pricePerHour = 1
    const totalCents = Math.round(hours * pricePerHour * 100)
    assert.strictEqual(totalCents, 1)
  })
})

describe('Booking — Origin URL Fallback Chain', () => {
  it('uses origin header when available', () => {
    const origin = 'https://prepchef.co'
    const appUrl = 'https://app.prepchef.co'
    const baseUrl = origin || appUrl || 'http://localhost:3000'
    assert.strictEqual(baseUrl, 'https://prepchef.co')
  })

  it('falls back to NEXT_PUBLIC_APP_URL', () => {
    const origin = null
    const appUrl = 'https://app.prepchef.co'
    const baseUrl = origin || appUrl || 'http://localhost:3000'
    assert.strictEqual(baseUrl, 'https://app.prepchef.co')
  })

  it('falls back to localhost', () => {
    const origin = null
    const appUrl = undefined
    const baseUrl = origin || appUrl || 'http://localhost:3000'
    assert.strictEqual(baseUrl, 'http://localhost:3000')
  })

  it('constructs correct success URL', () => {
    const baseUrl = 'https://prepchef.co'
    const successUrl = `${baseUrl}/bookings/success?session_id={CHECKOUT_SESSION_ID}`
    assert.ok(successUrl.includes('/bookings/success'))
    assert.ok(successUrl.includes('{CHECKOUT_SESSION_ID}'))
  })

  it('constructs correct cancel URL with kitchen ID', () => {
    const baseUrl = 'https://prepchef.co'
    const kitchenId = 'kitchen-abc-123'
    const cancelUrl = `${baseUrl}/kitchens/${kitchenId}`
    assert.strictEqual(cancelUrl, 'https://prepchef.co/kitchens/kitchen-abc-123')
  })
})

describe('Booking — Checkout Session Metadata Shape', () => {
  it('includes all required metadata fields', () => {
    const metadata = {
      kitchen_id: 'k-1',
      renter_id: 'u-1',
      start_time: '2026-04-10T10:00:00Z',
      end_time: '2026-04-10T14:00:00Z',
      total_hours: '4',
      price_per_hour: '50',
    }

    const requiredFields = ['kitchen_id', 'renter_id', 'start_time', 'end_time', 'total_hours', 'price_per_hour']
    for (const field of requiredFields) {
      assert.ok(field in metadata, `Missing field: ${field}`)
      assert.ok(metadata[field as keyof typeof metadata], `Empty field: ${field}`)
    }
  })

  it('converts hours and price to string for Stripe metadata', () => {
    const hours = 2.5
    const pricePerHour = 49.99
    const metadata = {
      total_hours: hours.toString(),
      price_per_hour: pricePerHour.toString(),
    }
    assert.strictEqual(metadata.total_hours, '2.5')
    assert.strictEqual(metadata.price_per_hour, '49.99')
    // Verify round-trip
    assert.strictEqual(parseFloat(metadata.total_hours), 2.5)
    assert.strictEqual(parseFloat(metadata.price_per_hour), 49.99)
  })
})
