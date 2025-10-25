import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../index';

test('returns default preferences for new user', async () => {
  const app = await createApp();
  const token = await app.jwt.sign({ sub: 'user-xyz', email: 'user@prep.test' });

  const res = await app.inject({
    method: 'GET',
    url: '/api/v1/notifications/preferences',
    headers: {
      authorization: `Bearer ${token}`
    }
  });

  assert.equal(res.statusCode, 200);
  const body = res.json();
  assert.equal(body.preferences.email, true);
  assert.equal(body.preferences.sms, false);
  assert.equal(body.preferences.in_app, true);
  assert.equal(body.preferences.push, true);

  await app.close();
});

