import { test } from 'node:test';
import assert from 'node:assert/strict';
import Fastify from 'fastify';
import cors from '@fastify/cors';

function build() {
  const app = Fastify();
  app.register(cors);
  app.get('/healthz', async () => ({ ok: true, svc: 'booking-svc' }));
  app.register(async function routes(instance) {
    instance.get('/', async () => ({ name: 'booking-svc' }));
  });
  return app;
}

test('GET / returns service name', async () => {
  const app = build();
  const res = await app.inject({ method: 'GET', url: '/' });
  assert.equal(res.statusCode, 200);
  assert.deepEqual(res.json(), { name: 'booking-svc' });
  await app.close();
});

test('GET /healthz reports ok', async () => {
  const app = build();
  const res = await app.inject({ method: 'GET', url: '/healthz' });
  assert.equal(res.statusCode, 200);
  assert.deepEqual(res.json(), { ok: true, svc: 'booking-svc' });
  await app.close();
});
