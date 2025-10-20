import Fastify from 'fastify';
import cors from '@fastify/cors';
import { log } from '@prep/logger';
import crypto from 'node:crypto';

export async function createApp() {
  const app = Fastify({ logger: false });
  await app.register(cors);

  app.get('/healthz', async () => ({ ok: true, svc: 'payments-svc' }));

  app.post('/intents', async (req, reply) => {
    const { amount_cents, metadata } = req.body as any;
    if (!amount_cents || amount_cents <= 0) {
      return reply.code(400).send({
        error: 'Invalid amount',
        message: 'Amount must be positive'
      });
    }
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

  app.register(async function routes(instance) {
    instance.get('/', async () => ({ name: 'payments-svc' }));
  });

  return app;
}

if (require.main === module) {
  const port = Number(process.env.PORT || 0) || Math.floor(Math.random() * 1000) + 3000;
  createApp().then(app => app.listen({ port }).then(() => log.info('payments-svc listening', port)));
}
