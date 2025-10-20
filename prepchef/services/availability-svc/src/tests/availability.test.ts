import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../index';

test('availability service health check', async () => {
  const app = await createApp();
  const res = await app.inject({
    method: 'GET',
    url: '/healthz'
  });

  assert.equal(res.statusCode, 200);
  assert.equal(res.json().ok, true);
  assert.equal(res.json().svc, 'availability-svc');
});

test('check availability for valid time slot', async () => {
  const app = await createApp();
  const res = await app.inject({
    method: 'POST',
    url: '/check',
    payload: {
      listing_id: '123e4567-e89b-12d3-a456-426614174000',
      starts_at: '2024-03-01T10:00:00Z',
      ends_at: '2024-03-01T14:00:00Z'
    }
  });

  assert.equal(res.statusCode, 204);
});

test('check availability for conflicting time slot', async () => {
  const app = await createApp();
  const res = await app.inject({
    method: 'POST',
    url: '/check',
    payload: {
      listing_id: 'conflict-test',
      starts_at: '2024-03-01T10:00:00Z',
      ends_at: '2024-03-01T14:00:00Z'
    }
  });

  assert.equal(res.statusCode, 409);
  const body = res.json();
  assert.ok(body.conflicts);
  assert.equal(body.conflicts.length, 1);
});

