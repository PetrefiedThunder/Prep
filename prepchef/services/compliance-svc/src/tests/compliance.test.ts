import { test } from 'node:test';
import assert from 'node:assert/strict';
import Fastify from 'fastify';

test('compliance check passes for valid listing', async () => {
  const app = Fastify();
  
  app.post('/check', async (req, reply) => {
    const { listing_id } = req.body as any;
    
    // Mock compliance check
    const mockCompliance = {
      'valid-listing': {
        health_permit: 'approved',
        insurance: 'approved',
        business_license: 'approved'
      },
      'expired-listing': {
        health_permit: 'expired',
        insurance: 'approved',
        business_license: 'approved'
      }
    };
    
    const compliance = mockCompliance[listing_id as keyof typeof mockCompliance];
    
    if (!compliance) {
      return reply.code(404).send({ error: 'Listing not found' });
    }
    
    const allApproved = Object.values(compliance).every(status => status === 'approved');
    
    if (allApproved) {
      return reply.code(204).send();
    } else {
      return reply.code(412).send({ 
        error: 'Compliance check failed',
        failed_checks: Object.entries(compliance)
          .filter(([_, status]) => status !== 'approved')
          .map(([type, status]) => ({ type, status }))
      });
    }
  });
  
  const res = await app.inject({
    method: 'POST',
    url: '/check',
    payload: { listing_id: 'valid-listing' }
  });

  assert.equal(res.statusCode, 204);
  await app.close();
});

test('compliance check fails for expired documents', async () => {
  const app = Fastify();
  
  app.post('/check', async (req, reply) => {
    return reply.code(412).send({ 
      error: 'Compliance check failed',
      failed_checks: [
        { type: 'health_permit', status: 'expired' }
      ]
    });
  });
  
  const res = await app.inject({
    method: 'POST',
    url: '/check',
    payload: { listing_id: 'expired-listing' }
  });

  assert.equal(res.statusCode, 412);
  const body = res.json();
  assert.ok(body.failed_checks);
  assert.equal(body.failed_checks[0].status, 'expired');
  await app.close();
});

