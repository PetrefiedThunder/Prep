import Fastify from 'fastify';
import { log } from '@prep/logger';
import { prepSecurityPlugin } from '@prep/common';

export async function createApp() {
  const app = Fastify({ logger: false });
  await app.register(prepSecurityPlugin, {
    serviceName: 'listing-svc'
  });

  app.get('/healthz', async () => ({ ok: true, svc: 'listing-svc' }));

  app.register(async function routes(instance) {
    instance.get('/', async () => ({ name: 'listing-svc' }));
  });

  return app;
}

if (require.main === module) {
  const port = Number(process.env.PORT || 0) || Math.floor(Math.random() * 1000) + 3000;
  createApp().then(app => app.listen({ port }).then(() => log.info('listing-svc listening', port)));
}
