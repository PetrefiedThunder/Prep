import { FastifyInstance } from 'fastify';

export default async function (app: FastifyInstance) {
  app.post('/access/provision', async (req, reply) => {
    // TODO: integrate with vendor; emit event
    return reply.send({ credentialId: 'cred_test_123', code: '123456' });
  });
  app.post('/access/revoke', async (req, reply) => {
    return reply.send({ revoked: true });
  });
}
