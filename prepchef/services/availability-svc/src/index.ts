import Fastify from 'fastify';
import cors from '@fastify/cors';
import { log } from '@prep/logger';

export async function createApp() {
  const app = Fastify({ logger: false });
  await app.register(cors);

  app.get('/healthz', async () => ({ ok: true, svc: 'availability-svc' }));

  app.post('/check', async (req, reply) => {
    const { listing_id } = req.body as any;
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

  app.register(async function routes(instance) {
    instance.get('/', async () => ({ name: 'availability-svc' }));
  });

  return app;
}

if (require.main === module) {
  const port = Number(process.env.PORT || 0) || Math.floor(Math.random() * 1000) + 3000;
  createApp().then(app => app.listen({ port }).then(() => log.info('availability-svc listening', port)));
}
