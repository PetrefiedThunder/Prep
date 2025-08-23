import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../index';

const validCreds = { username: 'admin', password: 'secret' };

test('issues tokens for valid credentials', async () => {
  const app = await createApp();
  const res = await app.inject({
    method: 'POST',
    url: '/auth/login',
    payload: validCreds,
  });
  assert.equal(res.statusCode, 200);
  const body = res.json();
  assert.ok(body.token);
  assert.ok(body.refreshToken);
  const decoded = await app.jwt.verify(body.token);
  assert.equal(decoded.username, 'admin');
});

test('rejects invalid credentials', async () => {
  const app = await createApp();
  const res = await app.inject({
    method: 'POST',
    url: '/auth/login',
    payload: { username: 'admin', password: 'wrong' },
  });
  assert.equal(res.statusCode, 401);
});

test('refreshes token with valid refresh token', async () => {
  const app = await createApp();
  const loginRes = await app.inject({
    method: 'POST',
    url: '/auth/login',
    payload: validCreds,
  });
  const { refreshToken } = loginRes.json();
  const refreshRes = await app.inject({
    method: 'POST',
    url: '/auth/refresh',
    payload: { refreshToken },
  });
  assert.equal(refreshRes.statusCode, 200);
  const body = refreshRes.json();
  assert.ok(body.token);
  assert.ok(body.refreshToken);
});

test('rejects invalid refresh token', async () => {
  const app = await createApp();
  const res = await app.inject({
    method: 'POST',
    url: '/auth/refresh',
    payload: { refreshToken: 'bogus' },
  });
  assert.equal(res.statusCode, 401);
});

test('cannot reuse refresh token after rotation', async () => {
  const app = await createApp();
  const loginRes = await app.inject({
    method: 'POST',
    url: '/auth/login',
    payload: validCreds,
  });
  const { refreshToken } = loginRes.json();

  // First refresh succeeds and rotates the token
  await app.inject({
    method: 'POST',
    url: '/auth/refresh',
    payload: { refreshToken },
  });

  // Second attempt with the same token should fail
  const secondRes = await app.inject({
    method: 'POST',
    url: '/auth/refresh',
    payload: { refreshToken },
  });
  assert.equal(secondRes.statusCode, 401);
});
