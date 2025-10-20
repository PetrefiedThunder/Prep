import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../index';

test('calculate pricing for booking', async () => {
  const app = await createApp();
  const res = await app.inject({
    method: 'POST',
    url: '/quote',
    payload: {
      listing_id: '123e4567-e89b-12d3-a456-426614174000',
      starts_at: '2024-03-01T10:00:00Z',
      ends_at: '2024-03-01T14:00:00Z'
    }
  });

  assert.equal(res.statusCode, 200);
  const body = res.json();
  assert.equal(body.hours, 4);
  assert.equal(body.hourly_rate_cents, 5000);
  assert.equal(body.subtotal_cents, 20000);
  assert.ok(body.total_cents > body.subtotal_cents);
});

test('pricing validation for invalid duration', async () => {
  const app = await createApp();

  // Test invalid duration
  const res1 = await app.inject({
    method: 'POST',
    url: '/quote',
    payload: {
      listing_id: '123',
      starts_at: '2024-03-01T10:00:00Z',
      ends_at: '2024-03-01T09:00:00Z' // End before start
    }
  });

  assert.equal(res1.statusCode, 400);
  assert.ok(res1.json().error.includes('Invalid'));

  // Test minimum duration
  const res2 = await app.inject({
    method: 'POST',
    url: '/quote',
    payload: {
      listing_id: '123',
      starts_at: '2024-03-01T10:00:00Z',
      ends_at: '2024-03-01T11:00:00Z' // Only 1 hour
    }
  });

  assert.equal(res2.statusCode, 400);
  assert.ok(res2.json().message.includes('2 hours'));
});

