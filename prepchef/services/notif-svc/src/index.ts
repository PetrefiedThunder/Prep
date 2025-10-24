import Fastify from 'fastify';
import { log } from '@prep/logger';
import { prepSecurityPlugin } from '@prep/common';
import crypto from 'node:crypto';

export async function createApp() {
  const app = Fastify({ logger: false });
  await app.register(prepSecurityPlugin, {
    serviceName: 'notif-svc'
  });

  app.get('/healthz', async () => ({ ok: true, svc: 'notif-svc' }));

  app.post('/send', async (req, reply) => {
    const { type, recipient_id, data } = req.body as any;
    if (!type || !recipient_id) {
      return reply.code(400).send({
        error: 'Missing required fields',
        message: 'type and recipient_id are required'
      });
    }
    const notification = {
      notification_id: crypto.randomUUID(),
      type,
      recipient_id,
      data: data || {},
      sent_at: new Date().toISOString(),
      channels: ['email', 'push']
    };
    return reply.code(202).send({
      notification_id: notification.notification_id,
      status: 'queued'
    });
  });

  app.register(async function routes(instance) {
    instance.get('/', async () => ({ name: 'notif-svc' }));
  });

  return app;
}

if (require.main === module) {
  const port = Number(process.env.PORT || 0) || Math.floor(Math.random() * 1000) + 3000;
  createApp().then(app => app.listen({ port }).then(() => log.info('notif-svc listening', port)));
}
