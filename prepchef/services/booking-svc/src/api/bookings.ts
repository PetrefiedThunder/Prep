import { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { ApiError } from '@prep/common';
import { fetch } from 'undici';

export default async function (app: FastifyInstance) {
  const Body = z.object({ listing_id: z.string().uuid(), starts_at: z.string(), ends_at: z.string() });
  app.post('/bookings', async (req, reply) => {
    const parsed = Body.safeParse(req.body);
    if (!parsed.success) return reply.code(400).send(ApiError('PC-REQ-400','Invalid body'));
    const { listing_id, starts_at, ends_at } = parsed.data;
    try {
      const comp = await fetch('http://compliance/check', { method: 'POST', body: JSON.stringify({ listing_id }) });
      if (!comp.ok) return reply.code(412).send(ApiError('PC-COMP-412', 'Compliance check failed'));

      const avail = await fetch('http://availability/check', { method: 'POST', body: JSON.stringify({ listing_id, starts_at, ends_at }) });
      if (!avail.ok) return reply.code(412).send(ApiError('PC-AVAIL-412', 'Listing not available'));

      const priceRes = await fetch('http://pricing/quote', { method: 'POST', body: JSON.stringify({ listing_id, starts_at, ends_at }) });
      if (!priceRes.ok) return reply.code(412).send(ApiError('PC-PRICE-412', 'Unable to calculate price'));
      const price = await priceRes.json();

      const payRes = await fetch('http://payments/intents', { method: 'POST', body: JSON.stringify({ listing_id, amount: price.amount }) });
      if (!payRes.ok) return reply.code(402).send(ApiError('PC-PAY-402', 'Payment failed'));
      const payment = await payRes.json();

      return reply.code(201).send({ booking_id: crypto.randomUUID(), payment_intent_id: payment.id });
    } catch (err) {
      app.log.error(err);
      return reply.code(500).send(ApiError('PC-BOOK-500', 'Unexpected error'));
    }
  });
}
