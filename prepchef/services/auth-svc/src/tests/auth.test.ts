import { test } from 'node:test';
import assert from 'node:assert/strict';
import Fastify from 'fastify';
import auth from '../api/auth';

function build() {
  const app = Fastify();
  app.register(auth);
  return app;
}

test('issues tokens on valid login', async () => {
  const app = build();
  await app.ready();

  const res = await app.inject({
    method: 'POST',
    url: '/auth/login',
    payload: { username: 'user', password: 'pass' }
  });

  assert.equal(res.statusCode, 200);
  const body = res.json();
  assert.ok(body.token);
  assert.ok(body.refreshToken);
  await app.close();
});

test('rejects invalid credentials', async () => {
  const app = build();
  await app.ready();

  const res = await app.inject({
    method: 'POST',
    url: '/auth/login',
    payload: { username: 'user', password: 'bad' }
  });

  assert.equal(res.statusCode, 401);
  await app.close();
});

test('refreshes token with valid refresh token', async () => {
  const app = build();
  await app.ready();

  const loginRes = await app.inject({
    method: 'POST',
    url: '/auth/login',
    payload: { username: 'user', password: 'pass' }
  });
  const { refreshToken } = loginRes.json();

  const refreshRes = await app.inject({
    method: 'POST',
    url: '/auth/refresh',
    payload: { refreshToken }
  });

  assert.equal(refreshRes.statusCode, 200);
  const refreshed = refreshRes.json();
  assert.ok(refreshed.token);
  assert.ok(refreshed.refreshToken);
  await app.close();
});

test('rejects invalid refresh token', async () => {
  const app = build();
  await app.ready();

  const res = await app.inject({
    method: 'POST',
    url: '/auth/refresh',
    payload: { refreshToken: 'bad' }
  });

  assert.equal(res.statusCode, 401);
  await app.close();
});

