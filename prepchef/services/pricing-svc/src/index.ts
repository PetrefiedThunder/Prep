import Fastify from 'fastify';
import cors from '@fastify/cors';
import { log } from '@prep/logger';

export async function createApp() {
  const app = Fastify({ logger: false });
  await app.register(cors);

  app.get('/healthz', async () => ({ ok: true, svc: 'pricing-svc' }));

  app.post('/quote', async (req, reply) => {
    const { listing_id, starts_at, ends_at } = req.body as any;
    const start = new Date(starts_at);
    const end = new Date(ends_at);

    if (isNaN(start.getTime()) || isNaN(end.getTime()) || end <= start) {
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

    const hourlyRate = 5000; // $50 in cents
    const subtotal = Math.round(hours * hourlyRate);
    const serviceFee = Math.round(subtotal * 0.15);
    const tax = Math.round((subtotal + serviceFee) * 0.0875);

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

  app.register(async function routes(instance) {
    instance.get('/', async () => ({ name: 'pricing-svc' }));
  });

  return app;
}

if (require.main === module) {
  const port = Number(process.env.PORT || 0) || Math.floor(Math.random() * 1000) + 3000;
  createApp().then(app => app.listen({ port }).then(() => log.info('pricing-svc listening', port)));
}
