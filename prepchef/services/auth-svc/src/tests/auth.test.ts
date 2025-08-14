import { test } from 'node:test';
import assert from 'node:assert/strict';
import Fastify from 'fastify';
import auth, { refreshTokens } from '../api/auth';

async function buildApp() {
  const app = Fastify();
  await app.register(auth);
  return app;
}

test('login success returns tokens', async (t) => {
  const app = await buildApp();
  t.after(async () => {
    await app.close();
    refreshTokens.clear();
  });
  const res = await app.inject({
    method: 'POST',
    url: '/auth/login',
    payload: { username: 'demo', password: 'password' },
  });
  assert.equal(res.statusCode, 200);
  const body = res.json();
  assert.ok(body.token);
  assert.ok(body.refreshToken);
});

test('login failure returns 401', async (t) => {
  const app = await buildApp();
  t.after(async () => {
    await app.close();
    refreshTokens.clear();
  });
  const res = await app.inject({
    method: 'POST',
    url: '/auth/login',
    payload: { username: 'demo', password: 'wrong' },
  });
  assert.equal(res.statusCode, 401);
});

test('refresh token flow', async (t) => {
  const app = await buildApp();
  t.after(async () => {
    await app.close();
    refreshTokens.clear();
  });
  const login = await app.inject({
    method: 'POST',
    url: '/auth/login',
    payload: { username: 'demo', password: 'password' },
  });
  const refreshToken = login.json().refreshToken;
  const res = await app.inject({
    method: 'POST',
    url: '/auth/refresh',
    payload: { refreshToken },
  });
  assert.equal(res.statusCode, 200);
  const body = res.json();
  assert.ok(body.token);
});
