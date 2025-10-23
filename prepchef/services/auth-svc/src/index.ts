import Fastify from 'fastify';
import { log } from '@prep/logger';
import { prepSecurityPlugin } from '@prep/common';
import auth from './api/auth';

export async function createApp() {
  const app = Fastify({ logger: false });
  await app.register(prepSecurityPlugin, {
    serviceName: 'auth-svc'
  });

  app.get('/healthz', async () => ({ ok: true, svc: 'auth-svc' }));

  app.register(async function routes(instance) {
    instance.get('/', async () => ({ name: 'auth-svc' }));
  });

  await app.register(auth);

  return app;
}

if (require.main === module) {
  const port = Number(process.env.PORT || 0) || Math.floor(Math.random() * 1000) + 3000;
  createApp().then(app => app.listen({ port }).then(() => log.info('auth-svc listening', port)));
}
