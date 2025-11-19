import Fastify from 'fastify';
import cors from '@fastify/cors';
import { log } from '@prep/logger';
import { prepSecurityPlugin } from '@prep/common';
import availability from './api/availability';

export async function createApp() {
  const app = Fastify({ logger: false });
  await app.register(cors);
  await app.register(prepSecurityPlugin, {
    serviceName: 'availability-svc'
  });

  app.get('/healthz', async () => ({ ok: true, svc: 'availability-svc' }));

  app.register(async function routes(instance) {
    instance.get('/', async () => ({ name: 'availability-svc' }));
  });

  await app.register(availability);

  return app;
}

if (require.main === module) {
  const port = Number(process.env.PORT || 0) || Math.floor(Math.random() * 1000) + 3000;
  createApp().then(app => app.listen({ port }).then(() => log.info('availability-svc listening', { port })));
}
