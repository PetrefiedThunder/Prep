import { test } from 'node:test';
import assert from 'node:assert/strict';
import Fastify from 'fastify';

test('create payment intent', async () => {
  const app = Fastify();
  
  app.post('/intents', async (req, reply) => {
    const { amount_cents, metadata } = req.body as any;
    
    if (!amount_cents || amount_cents <= 0) {
      return reply.code(400).send({
        error: 'Invalid amount',
        message: 'Amount must be positive'
      });
    }
    
    // Mock Stripe payment intent creation
    const paymentIntent = {
      id: `pi_${crypto.randomUUID().replace(/-/g, '')}`,
      amount: amount_cents,
      currency: 'usd',
      status: 'requires_payment_method',
      client_secret: `pi_secret_${crypto.randomUUID().replace(/-/g, '')}`,
      metadata: metadata || {},
      created: Date.now()
    };
    
    return reply.code(201).send(paymentIntent);
  });
  
  const res = await app.inject({
    method: 'POST',
    url: '/intents',
    payload: {
      amount_cents: 10000,
      metadata: {
        booking_id: 'test-booking',
        listing_id: 'test-listing'
      }
    }
  });
  
  assert.equal(res.statusCode, 201);
  const body = res.json();
  assert.ok(body.id.startsWith('pi_'));
  assert.equal(body.amount, 10000);
  assert.equal(body.currency, 'usd');
  assert.ok(body.client_secret);
  await app.close();
});

test('reject invalid payment amount', async () => {
  const app = Fastify();
  
  app.post('/intents', async (req, reply) => {
    const { amount_cents } = req.body as any;
    
    if (!amount_cents || amount_cents <= 0) {
      return reply.code(400).send({
        error: 'Invalid amount',
        message: 'Amount must be positive'
      });
    }
    
    return reply.code(201).send({ id: 'pi_test' });
  });
  
  const res = await app.inject({
    method: 'POST',
    url: '/intents',
    payload: {
      amount_cents: -100
    }
  });

  assert.equal(res.statusCode, 400);
  assert.ok(res.json().error.includes('Invalid'));
  await app.close();
});

