import { test } from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { createApp } from '../index';

test('create payment intent', async () => {
  const app = await createApp();
  const res = await app.inject({
    method: 'POST',
    url: '/intents',
    payload: {
      amount_cents: 10000,
      metadata: {
        booking_id: 'test-booking',
        listing_id: 'test-listing'
      }
    }
  });

  assert.equal(res.statusCode, 201);
  const body = res.json();
  assert.ok(body.id.startsWith('pi_'));
  assert.equal(body.amount, 10000);
  assert.equal(body.currency, 'usd');
  assert.ok(body.client_secret);
  await app.close();
});

test('reject invalid payment amount', async () => {
  const app = await createApp();
  const res = await app.inject({
    method: 'POST',
    url: '/intents',
    payload: {
      amount_cents: -100
    }
  });

  assert.equal(res.statusCode, 400);
  assert.ok(res.json().error.includes('Invalid'));
  await app.close();
});

test('reject webhook with invalid signature', async () => {
  const secret = 'whsec_test_invalid';
  process.env.STRIPE_WEBHOOK_SECRET = secret;
  const app = await createApp();

  try {
    const payload = JSON.stringify({
      id: 'evt_test',
      type: 'payment_intent.succeeded',
      data: { object: { id: 'pi_test', metadata: { booking_id: 'booking-1' } } }
    });

    const res = await app.inject({
      method: 'POST',
      url: '/payments/webhook',
      payload,
      headers: {
        'content-type': 'application/json',
        'stripe-signature': 't=12345,v1=bad'
      }
    });

    assert.equal(res.statusCode, 400);
    assert.match(res.json().error, /signature/i);
  } finally {
    await app.close();
    delete process.env.STRIPE_WEBHOOK_SECRET;
  }
});

test('marks booking paid on payment_intent.succeeded webhook', async () => {
  const secret = 'whsec_test_valid';
  process.env.STRIPE_WEBHOOK_SECRET = secret;
  const app = await createApp();

  try {
    const bookingId = 'booking-42';
    const intentResponse = await app.inject({
      method: 'POST',
      url: '/intents',
      payload: {
        amount_cents: 2500,
        metadata: { booking_id: bookingId }
      }
    });

    const intentBody = intentResponse.json();

    const event = {
      id: 'evt_123',
      type: 'payment_intent.succeeded',
      data: {
        object: {
          id: intentBody.id,
          metadata: { booking_id: bookingId },
          amount: intentBody.amount,
          currency: intentBody.currency
        }
      }
    };

    const payload = JSON.stringify(event);
    const timestamp = Math.floor(Date.now() / 1000);
    const signature = crypto.createHmac('sha256', secret).update(`${timestamp}.${payload}`, 'utf8').digest('hex');

    const webhookRes = await app.inject({
      method: 'POST',
      url: '/payments/webhook',
      payload,
      headers: {
        'content-type': 'application/json',
        'stripe-signature': `t=${timestamp},v1=${signature}`
      }
    });

    assert.equal(webhookRes.statusCode, 200);
    assert.deepEqual(webhookRes.json(), { received: true });
    assert.equal(app.bookingPayments.get(bookingId)?.paid, true);
    assert.equal(app.bookingPayments.get(bookingId)?.paymentIntentId, intentBody.id);
    assert.equal(app.paymentIntents.get(intentBody.id)?.paid, true);
  } finally {
    await app.close();
    delete process.env.STRIPE_WEBHOOK_SECRET;
  }
});

