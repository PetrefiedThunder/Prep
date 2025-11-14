import Fastify from 'fastify';
import { log } from '@prep/logger';
import { prepSecurityPlugin } from '@prep/common';

export async function createApp() {
  const app = Fastify({ logger: false });
  await app.register(prepSecurityPlugin, {
    serviceName: 'compliance-svc'
  });

  app.get('/healthz', async () => ({ ok: true, svc: 'compliance-svc' }));

  app.post('/check', async (req, reply) => {
    const { listing_id } = req.body as any;
    const mockCompliance: Record<string, Record<string, string>> = {
      'valid-listing': {
        health_permit: 'approved',
        insurance: 'approved',
        business_license: 'approved'
      },
      'expired-listing': {
        health_permit: 'expired',
        insurance: 'approved',
        business_license: 'approved'
      }
    };

    const compliance = mockCompliance[listing_id as keyof typeof mockCompliance];

    if (!compliance) {
      return reply.code(404).send({ error: 'Listing not found' });
    }

    const allApproved = Object.values(compliance).every(status => status === 'approved');
    if (allApproved) {
      return reply.code(204).send();
    }

    return reply.code(412).send({
      error: 'Compliance check failed',
      failed_checks: Object.entries(compliance)
        .filter(([, status]) => status !== 'approved')
        .map(([type, status]) => ({ type, status }))
    });
  });

  app.register(async function routes(instance) {
    instance.get('/', async () => ({ name: 'compliance-svc' }));
  });

  return app;
}

if (require.main === module) {
  const port = Number(process.env.PORT || 0) || Math.floor(Math.random() * 1000) + 3000;
  createApp().then(app => app.listen({ port }).then(() => log.info('compliance-svc listening', { port })));
}
