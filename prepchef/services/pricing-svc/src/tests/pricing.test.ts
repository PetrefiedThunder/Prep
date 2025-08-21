import { test } from 'node:test';
import assert from 'node:assert/strict';
import Fastify from 'fastify';

test('calculate pricing for booking', async () => {
  const app = Fastify();
  
  app.post('/quote', async (req, reply) => {
    const { listing_id, starts_at, ends_at } = req.body as any;
    
    // Calculate hours
    const start = new Date(starts_at);
    const end = new Date(ends_at);
    const hours = (end.getTime() - start.getTime()) / (1000 * 60 * 60);
    
    // Mock pricing
    const hourlyRate = 5000; // $50 in cents
    const subtotal = Math.round(hours * hourlyRate);
    const serviceFee = Math.round(subtotal * 0.15); // 15% platform fee
    const tax = Math.round((subtotal + serviceFee) * 0.0875); // 8.75% tax
    
    return reply.send({
      listing_id,
      hours,
      hourly_rate_cents: hourlyRate,
      subtotal_cents: subtotal,
      service_fee_cents: serviceFee,
      tax_cents: tax,
      total_cents: subtotal + serviceFee + tax
    });
  });
  
  const res = await app.inject({
    method: 'POST',
    url: '/quote',
    payload: {
      listing_id: '123e4567-e89b-12d3-a456-426614174000',
      starts_at: '2024-03-01T10:00:00Z',
      ends_at: '2024-03-01T14:00:00Z'
    }
  });
  
  assert.equal(res.statusCode, 200);
  const body = res.json();
  assert.equal(body.hours, 4);
  assert.equal(body.hourly_rate_cents, 5000);
  assert.equal(body.subtotal_cents, 20000);
  assert.ok(body.total_cents > body.subtotal_cents);
});

test('pricing validation for invalid duration', async () => {
  const app = Fastify();
  
  app.post('/quote', async (req, reply) => {
    const { starts_at, ends_at } = req.body as any;
    
    const start = new Date(starts_at);
    const end = new Date(ends_at);
    
    if (end <= start) {
      return reply.code(400).send({
        error: 'Invalid duration',
        message: 'End time must be after start time'
      });
    }
    
    const hours = (end.getTime() - start.getTime()) / (1000 * 60 * 60);
    
    if (hours < 2) {
      return reply.code(400).send({
        error: 'Minimum duration not met',
        message: 'Minimum booking duration is 2 hours'
      });
    }
    
    return reply.send({ hours });
  });
  
  // Test invalid duration
  const res1 = await app.inject({
    method: 'POST',
    url: '/quote',
    payload: {
      listing_id: '123',
      starts_at: '2024-03-01T10:00:00Z',
      ends_at: '2024-03-01T09:00:00Z' // End before start
    }
  });
  
  assert.equal(res1.statusCode, 400);
  assert.ok(res1.json().error.includes('Invalid'));
  
  // Test minimum duration
  const res2 = await app.inject({
    method: 'POST',
    url: '/quote',
    payload: {
      listing_id: '123',
      starts_at: '2024-03-01T10:00:00Z',
      ends_at: '2024-03-01T11:00:00Z' // Only 1 hour
    }
  });
  
  assert.equal(res2.statusCode, 400);
  assert.ok(res2.json().message.includes('2 hours'));
});

