import { FastifyInstance } from 'fastify';

export default async function (app: FastifyInstance) {
  app.post('/auth/login', async (_req, reply) => {
    // TODO: real JWT implementation
    return reply.send({ token: 'dev.jwt.token' });
  });
}
