import Fastify from 'fastify';
import cors from '@fastify/cors';
import { log } from '@prep/logger';

export async function createApp() {
  const app = Fastify({ logger: false });
  await app.register(cors);

  app.get('/healthz', async () => ({ ok: true, svc: 'audit-svc' }));

  app.register(async function routes(instance) {
    instance.get('/', async () => ({ name: 'audit-svc' }));
  });

  return app;
}

if (require.main === module) {
  const port = Number(process.env.PORT || 0) || Math.floor(Math.random() * 1000) + 3000;
  createApp().then(app => app.listen({ port }).then(() => log.info('audit-svc listening', port)));
}
