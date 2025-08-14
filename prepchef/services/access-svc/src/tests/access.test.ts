import { test } from 'node:test';
import assert from 'node:assert/strict';
import Fastify from 'fastify';
import access from '../api/access';
import { messageBus } from '../adapters/messageBus';

test('provisions access and emits event', async () => {
  const app = Fastify();
  await app.register(access);

  const events: any[] = [];
  messageBus.once('access.provisioned', (payload) => events.push(payload));

  const res = await app.inject({
    method: 'POST',
    url: '/access/provision',
    payload: { userId: 'u1', resourceId: 'r1' }
  });

  assert.equal(res.statusCode, 200);
  const body = res.json();
  assert.equal(body.credentialId, 'cred_test_123');
  assert.equal(events[0].credentialId, 'cred_test_123');
});

test('revokes access and emits event', async () => {
  const app = Fastify();
  await app.register(access);

  const events: any[] = [];
  messageBus.once('access.revoked', (payload) => events.push(payload));

  const res = await app.inject({
    method: 'POST',
    url: '/access/revoke',
    payload: { credentialId: 'cred_test_123' }
  });

  assert.equal(res.statusCode, 200);
  const body = res.json();
  assert.equal(body.revoked, true);
  assert.equal(events[0].credentialId, 'cred_test_123');
});
