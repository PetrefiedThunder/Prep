import { test } from 'node:test';
import assert from 'node:assert/strict';
import '@fastify/jwt';

process.env.AUTH_PERSISTENCE = 'memory';
process.env.JWT_SECRET = 'test-secret-key-for-testing-at-least-32-chars-long';
process.env.AUTH_PASSWORD_SALT_ROUNDS = '4';

const { createApp } = await import('../index');

const validCreds = { username: 'admin', password: 'secret' };

async function createTestApp() {
  const app = await createApp();
  return app;
}

test('registers a new account and returns tokens', async () => {
  const app = await createTestApp();
  
  // Debug: check if jwt methods are available
  console.log('app.jwt:', typeof app.jwt);
  console.log('Methods on app:', Object.keys(app));
  
  const res = await app.inject({
    method: 'POST',
    url: '/auth/register',
    payload: {
      username: 'newhost',
      email: 'newhost@example.com',
      fullName: 'New Host',
      password: 'supersecret',
      role: 'host'
    }
  });

  if (res.statusCode !== 201) {
    console.error('Register failed:', res.statusCode, res.body);
  }
  assert.equal(res.statusCode, 201);
  const body = res.json();
  assert.ok(body.token);
  assert.ok(body.refreshToken);
  assert.equal(body.user.username, 'newhost');
  assert.equal(body.user.role, 'host');
  await app.close();
});

test('issues tokens for valid credentials', async () => {
  const app = await createTestApp();
  const res = await app.inject({
    method: 'POST',
    url: '/auth/login',
    payload: validCreds
  });
  assert.equal(res.statusCode, 200);
  const body = res.json();
  assert.ok(body.token);
  assert.ok(body.refreshToken);
  const decoded = await app.jwt.verify(body.token);
  assert.equal(decoded.username, 'admin');
  await app.close();
});

test('rejects invalid credentials', async () => {
  const app = await createTestApp();
  const res = await app.inject({
    method: 'POST',
    url: '/auth/login',
    payload: { username: 'admin', password: 'wrong' }
  });
  assert.equal(res.statusCode, 401);
  await app.close();
});

test('refreshes token with valid refresh token', async () => {
  const app = await createTestApp();
  const loginRes = await app.inject({
    method: 'POST',
    url: '/auth/login',
    payload: validCreds
  });
  const { refreshToken } = loginRes.json();
  const refreshRes = await app.inject({
    method: 'POST',
    url: '/auth/refresh',
    payload: { refreshToken }
  });
  assert.equal(refreshRes.statusCode, 200);
  const body = refreshRes.json();
  assert.ok(body.token);
  assert.ok(body.refreshToken);
  await app.close();
});

test('rejects invalid refresh token', async () => {
  const app = await createTestApp();
  const res = await app.inject({
    method: 'POST',
    url: '/auth/refresh',
    payload: { refreshToken: 'bogus' }
  });
  assert.equal(res.statusCode, 401);
  await app.close();
});

test('cannot reuse refresh token after rotation', async () => {
  const app = await createTestApp();
  const loginRes = await app.inject({
    method: 'POST',
    url: '/auth/login',
    payload: validCreds
  });
  const { refreshToken } = loginRes.json();

  await app.inject({
    method: 'POST',
    url: '/auth/refresh',
    payload: { refreshToken }
  });

  const secondRes = await app.inject({
    method: 'POST',
    url: '/auth/refresh',
    payload: { refreshToken }
  });
  assert.equal(secondRes.statusCode, 401);
  await app.close();
});
