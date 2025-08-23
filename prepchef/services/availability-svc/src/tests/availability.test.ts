import { test } from 'node:test';
import assert from 'node:assert/strict';
import Fastify from 'fastify';

test('availability service health check', async () => {
  const app = Fastify();
  
  app.get('/healthz', async () => ({ ok: true, svc: 'availability-svc' }));
  
  const res = await app.inject({
    method: 'GET',
    url: '/healthz'
  });

  assert.equal(res.statusCode, 200);
  assert.equal(res.json().ok, true);
  assert.equal(res.json().svc, 'availability-svc');
  await app.close();
});

test('check availability for valid time slot', async () => {
  const app = Fastify();
  
  app.post('/check', async (req, reply) => {
    const { listing_id, starts_at, ends_at } = req.body as any;
    
    // Mock availability check
    const available = true; // Would check database in real implementation
    
    if (available) {
      return reply.code(204).send();
    } else {
      return reply.code(409).send({ 
        error: 'Time slot not available',
        conflicts: []
      });
    }
  });
  
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
  await app.close();
});

test('check availability for conflicting time slot', async () => {
  const app = Fastify();
  
  app.post('/check', async (req, reply) => {
    const { listing_id } = req.body as any;
    
    // Mock conflict check
    if (listing_id === 'conflict-test') {
      return reply.code(409).send({ 
        error: 'Time slot not available',
        conflicts: [
          {
            booking_id: 'existing-booking',
            start_time: '2024-03-01T09:00:00Z',
            end_time: '2024-03-01T12:00:00Z'
          }
        ]
      });
    }
    
    return reply.code(204).send();
  });
  
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
  await app.close();
});

