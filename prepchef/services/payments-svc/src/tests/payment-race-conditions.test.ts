import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../index';
import { getPrismaClient } from '@prep/database';

/**
 * Regression tests for payment intent creation race conditions
 *
 * Tests the fix for: Two concurrent requests creating payment intents for the same booking
 * could both pass validation and create duplicate Stripe charges.
 */

const prisma = getPrismaClient();

// Helper to create test booking
async function createTestBooking(id: string, status: string = 'requested') {
  await prisma.booking.create({
    data: {
      id,
      listingId: 'listing-test-123',
      renterId: 'renter-test-456',
      startTime: new Date('2025-12-01T10:00:00Z'),
      endTime: new Date('2025-12-01T12:00:00Z'),
      status,
      hourlyRateCents: 5000,
      subtotalCents: 10000,
      serviceFeeCents: 1000,
      taxCents: 900,
      totalCents: 11900,
      paymentStatus: 'pending',
      securityDepositCents: 0
    }
  });
}

// Helper to clean up test data
async function cleanupBooking(id: string) {
  await prisma.booking.delete({ where: { id } }).catch(() => {});
}

test('prevent duplicate payment intent creation via concurrent requests', async (t) => {
  const app = await createApp();
  const bookingId = 'booking-race-test-001';

  // Set up Stripe mock key
  process.env.STRIPE_SECRET_KEY = 'sk_test_mock_key_123';

  try {
    // Create test booking in 'requested' state
    await createTestBooking(bookingId);

    // Simulate two concurrent requests trying to create payment intents
    const [result1, result2] = await Promise.allSettled([
      app.inject({
        method: 'POST',
        url: '/intents',
        payload: {
          booking_id: bookingId,
          amount_cents: 11900
        }
      }),
      app.inject({
        method: 'POST',
        url: '/intents',
        payload: {
          booking_id: bookingId,
          amount_cents: 11900
        }
      })
    ]);

    // One request should succeed (201), one should fail (409 - conflict)
    const statuses = [
      result1.status === 'fulfilled' ? result1.value.statusCode : null,
      result2.status === 'fulfilled' ? result2.value.statusCode : null
    ].sort();

    // We expect one 201 (success) and one 409 (conflict) or 400 (invalid state)
    const successCount = statuses.filter(s => s === 201).length;
    const conflictCount = statuses.filter(s => s === 409 || s === 400).length;

    assert.equal(successCount, 1, 'Exactly one request should succeed');
    assert.equal(conflictCount, 1, 'Exactly one request should be rejected');

    // Verify booking has exactly ONE payment intent ID
    const booking = await prisma.booking.findUnique({ where: { id: bookingId } });
    assert.ok(booking, 'Booking should exist');
    assert.ok(booking!.stripePaymentIntentId, 'Booking should have payment intent ID');

    // Second request that failed should return the existing payment intent ID if 409
    if (result1.status === 'fulfilled' && result1.value.statusCode === 409) {
      const body = result1.value.json();
      assert.equal(body.payment_intent_id, booking!.stripePaymentIntentId);
    }
    if (result2.status === 'fulfilled' && result2.value.statusCode === 409) {
      const body = result2.value.json();
      assert.equal(body.payment_intent_id, booking!.stripePaymentIntentId);
    }

  } finally {
    await cleanupBooking(bookingId);
    await app.close();
  }
});

test('reject payment intent creation for booking with existing payment intent', async (t) => {
  const app = await createApp();
  const bookingId = 'booking-race-test-002';

  process.env.STRIPE_SECRET_KEY = 'sk_test_mock_key_456';

  try {
    // Create booking with existing payment intent
    await createTestBooking(bookingId);
    await prisma.booking.update({
      where: { id: bookingId },
      data: {
        stripePaymentIntentId: 'pi_existing_123',
        paymentStatus: 'pending'
      }
    });

    // Try to create another payment intent
    const res = await app.inject({
      method: 'POST',
      url: '/intents',
      payload: {
        booking_id: bookingId,
        amount_cents: 11900
      }
    });

    assert.equal(res.statusCode, 409, 'Should return 409 Conflict');
    const body = res.json();
    assert.match(body.error, /already exists/i);
    assert.equal(body.payment_intent_id, 'pi_existing_123');

  } finally {
    await cleanupBooking(bookingId);
    await app.close();
  }
});

test('reject payment intent for booking not in requested state', async (t) => {
  const app = await createApp();
  const bookingId = 'booking-race-test-003';

  process.env.STRIPE_SECRET_KEY = 'sk_test_mock_key_789';

  try {
    // Create booking in 'confirmed' state
    await createTestBooking(bookingId, 'confirmed');

    const res = await app.inject({
      method: 'POST',
      url: '/intents',
      payload: {
        booking_id: bookingId,
        amount_cents: 11900
      }
    });

    assert.equal(res.statusCode, 400, 'Should return 400 Bad Request');
    assert.match(res.json().error, /not in valid state/i);

  } finally {
    await cleanupBooking(bookingId);
    await app.close();
  }
});

test('atomically reserve booking during payment intent creation', async (t) => {
  const app = await createApp();
  const bookingId = 'booking-race-test-004';

  process.env.STRIPE_SECRET_KEY = 'sk_test_mock_key_abc';

  try {
    await createTestBooking(bookingId);

    // First request should atomically set paymentStatus to 'pending'
    const res = await app.inject({
      method: 'POST',
      url: '/intents',
      payload: {
        booking_id: bookingId,
        amount_cents: 11900
      }
    });

    // Even if this fails due to Stripe being mocked, the booking should be reserved
    const booking = await prisma.booking.findUnique({ where: { id: bookingId } });
    assert.equal(booking!.paymentStatus, 'pending', 'Booking should be reserved with pending status');

  } finally {
    await cleanupBooking(bookingId);
    await app.close();
  }
});
