import Fastify from 'fastify';
import cors from '@fastify/cors';
import { log } from '@prep/logger';
import access from './api/access';

export async function createApp() {
  const app = Fastify({ logger: false });
  await app.register(cors);

  app.get('/healthz', async () => ({ ok: true, svc: 'access-svc' }));

  app.register(async function routes(instance) {
    instance.get('/', async () => ({ name: 'access-svc' }));
  });

  await app.register(access);

  return app;
}

if (require.main === module) {
  const port = Number(process.env.PORT || 0) || Math.floor(Math.random() * 1000) + 3000;
  createApp().then(app => app.listen({ port }).then(() => log.info('access-svc listening', port)));
}
