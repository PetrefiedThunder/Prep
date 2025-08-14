import { FastifyInstance } from 'fastify';
import { accessProvider } from '../adapters/accessProvider';
import { messageBus } from '../adapters/messageBus';

export default async function (app: FastifyInstance) {
  app.post('/access/provision', async (req, reply) => {
    const { userId, resourceId } = req.body as any;
    const credential = await accessProvider.provision({ userId, resourceId });
    messageBus.emit('access.provisioned', { userId, resourceId, ...credential });
    return reply.send(credential);
  });
  app.post('/access/revoke', async (req, reply) => {
    const { credentialId } = req.body as any;
    const result = await accessProvider.revoke({ credentialId });
    messageBus.emit('access.revoked', { credentialId });
    return reply.send(result);
  });
}
