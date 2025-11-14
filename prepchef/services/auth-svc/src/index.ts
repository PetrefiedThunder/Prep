import Fastify from 'fastify';
import { log } from '@prep/logger';
import { prepSecurityPlugin } from '@prep/common';
import { env } from '@prep/config';
import auth from './api/auth';
import { createUserStore, type UserStore } from './data/user-store';

declare module 'fastify' {
  interface FastifyInstance {
    userStore: UserStore;
  }
}

export async function createApp() {
  const app = Fastify({ logger: false });
  const userStore = await createUserStore();
  await userStore.ensureDefaultAdmin();

  await app.register(prepSecurityPlugin, {
    serviceName: 'auth-svc',
    jwt: {
      secret: env.JWT_SECRET,
      sign: { expiresIn: env.AUTH_ACCESS_TOKEN_TTL }
    }
  });

  app.decorate('userStore', userStore);

  app.addHook('onClose', async instance => {
    await instance.userStore.close();
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
  createApp().then(app => app.listen({ port }).then(() => log.info('auth-svc listening', { port })));
}
