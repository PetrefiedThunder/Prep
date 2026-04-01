import assert from 'node:assert'
import { describe, it } from 'node:test'

/**
 * Tests for booking business logic extracted from lib/actions/bookings.ts.
 *
 * The server action createCheckoutSession contains several critical
 * validations and calculations. We extract the pure logic here to
 * test without Next.js server context dependencies.
 */

// Extracted from createCheckoutSession: hour calculation
function calculateHours(startTime: string, endTime: string): number {
  const start = new Date(startTime)
  const end = new Date(endTime)
  return (end.getTime() - start.getTime()) / (1000 * 60 * 60)
}

// Extracted from createCheckoutSession: amount calculation
function calculateCheckoutAmount(hours: number, pricePerHour: number) {
  const totalAmount = Math.round(hours * pricePerHour * 100) // cents
  const platformFeePercent = 0.10
  const platformFee = Math.round(totalAmount * platformFeePercent)
  return { totalAmount, platformFee }
}

// Extracted overlap check logic
function timesOverlap(
  reqStart: Date, reqEnd: Date,
  existStart: Date, existEnd: Date
): boolean {
  return reqStart < existEnd && reqEnd > existStart
}

describe('calculateHours', () => {
  it('calculates 3 hours correctly', () => {
    const hours = calculateHours('2026-04-01T09:00:00Z', '2026-04-01T12:00:00Z')
    assert.strictEqual(hours, 3)
  })

  it('calculates fractional hours (1.5h)', () => {
    const hours = calculateHours('2026-04-01T09:00:00Z', '2026-04-01T10:30:00Z')
    assert.strictEqual(hours, 1.5)
  })

  it('returns 0 for same start and end time', () => {
    const hours = calculateHours('2026-04-01T09:00:00Z', '2026-04-01T09:00:00Z')
    assert.strictEqual(hours, 0)
  })

  it('returns negative for end before start (invalid)', () => {
    const hours = calculateHours('2026-04-01T12:00:00Z', '2026-04-01T09:00:00Z')
    assert.ok(hours < 0)
  })

  it('handles overnight bookings', () => {
    const hours = calculateHours('2026-04-01T22:00:00Z', '2026-04-02T06:00:00Z')
    assert.strictEqual(hours, 8)
  })
})

describe('calculateCheckoutAmount', () => {
  it('calculates $150 for 3h at $50/hr', () => {
    const { totalAmount, platformFee } = calculateCheckoutAmount(3, 50)
    assert.strictEqual(totalAmount, 15000) // cents
    assert.strictEqual(platformFee, 1500)  // 10%
  })

  it('rounds to nearest cent for fractional amounts', () => {
    // 1.5h at $33/hr = $49.50 = 4950 cents
    const { totalAmount, platformFee } = calculateCheckoutAmount(1.5, 33)
    assert.strictEqual(totalAmount, 4950)
    assert.strictEqual(platformFee, 495)
  })

  it('handles zero hours', () => {
    const { totalAmount, platformFee } = calculateCheckoutAmount(0, 50)
    assert.strictEqual(totalAmount, 0)
    assert.strictEqual(platformFee, 0)
  })

  it('handles very small amounts', () => {
    const { totalAmount, platformFee } = calculateCheckoutAmount(0.5, 1)
    assert.strictEqual(totalAmount, 50) // $0.50
    assert.strictEqual(platformFee, 5)  // $0.05
  })

  it('handles large amounts without overflow', () => {
    const { totalAmount, platformFee } = calculateCheckoutAmount(24, 500)
    assert.strictEqual(totalAmount, 1200000) // $12,000
    assert.strictEqual(platformFee, 120000)  // $1,200
  })
})

describe('timesOverlap (booking conflict detection)', () => {
  const d = (h: number) => new Date(`2026-04-01T${String(h).padStart(2, '0')}:00:00Z`)

  it('detects overlap when new booking starts during existing', () => {
    // Existing: 9-12, New: 10-13
    assert.strictEqual(timesOverlap(d(10), d(13), d(9), d(12)), true)
  })

  it('detects overlap when new booking ends during existing', () => {
    // Existing: 10-14, New: 8-11
    assert.strictEqual(timesOverlap(d(8), d(11), d(10), d(14)), true)
  })

  it('detects overlap when new booking fully contains existing', () => {
    // Existing: 10-12, New: 9-13
    assert.strictEqual(timesOverlap(d(9), d(13), d(10), d(12)), true)
  })

  it('detects overlap when existing fully contains new', () => {
    // Existing: 9-14, New: 10-12
    assert.strictEqual(timesOverlap(d(10), d(12), d(9), d(14)), true)
  })

  it('no overlap when new ends exactly at existing start (adjacent)', () => {
    // Existing: 12-14, New: 9-12
    assert.strictEqual(timesOverlap(d(9), d(12), d(12), d(14)), false)
  })

  it('no overlap when new starts exactly at existing end (adjacent)', () => {
    // Existing: 9-12, New: 12-14
    assert.strictEqual(timesOverlap(d(12), d(14), d(9), d(12)), false)
  })

  it('no overlap for completely separate time slots', () => {
    // Existing: 9-10, New: 14-16
    assert.strictEqual(timesOverlap(d(14), d(16), d(9), d(10)), false)
  })

  it('detects exact same time slot as overlap', () => {
    assert.strictEqual(timesOverlap(d(9), d(12), d(9), d(12)), true)
  })
})
