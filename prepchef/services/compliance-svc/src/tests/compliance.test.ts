import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../index';

test('compliance check passes for valid listing', async () => {
  const app = await createApp();
  const res = await app.inject({
    method: 'POST',
    url: '/check',
    payload: { listing_id: 'valid-listing' }
  });

  assert.equal(res.statusCode, 204);
  await app.close();
});

test('compliance check fails for expired documents', async () => {
  const app = await createApp();
  const res = await app.inject({
    method: 'POST',
    url: '/check',
    payload: { listing_id: 'expired-listing' }
  });

  assert.equal(res.statusCode, 412);
  const body = res.json();
  assert.ok(body.failed_checks);
  assert.equal(body.failed_checks[0].status, 'expired');
  await app.close();
});

