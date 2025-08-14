import { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { ApiError } from '@prep/common';

export default async function (app: FastifyInstance) {
  const Body = z.object({ listing_id: z.string().uuid(), starts_at: z.string(), ends_at: z.string() });
  app.post('/bookings', async (req, reply) => {
    const parsed = Body.safeParse(req.body);
    if (!parsed.success) return reply.code(400).send(ApiError('PC-REQ-400','Invalid body'));
    // TODO: call compliance, availability, pricing, payments
    return reply.code(201).send({ booking_id: crypto.randomUUID(), payment_intent_id: 'pi_test_123' });
  });
}
