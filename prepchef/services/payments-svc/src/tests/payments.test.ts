import { test } from 'node:test';
import assert from 'node:assert/strict';
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

