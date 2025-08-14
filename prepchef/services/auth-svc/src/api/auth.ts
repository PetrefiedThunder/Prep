import { FastifyInstance } from 'fastify';
import fastifyJwt from '@fastify/jwt';

const refreshTokens = new Map<string, string>();

export default async function (app: FastifyInstance) {
  app.register(fastifyJwt, {
    secret: process.env.JWT_SECRET || 'supersecret',
  });

  app.post('/auth/login', async (req, reply) => {
    const { username, password } = req.body as any;
    if (username !== 'admin' || password !== 'secret') {
      return reply.code(401).send({ error: 'Invalid credentials' });
    }
    const token = await reply.jwtSign({ username });
    const refreshToken = await reply.jwtSign(
      { username },
      { expiresIn: '7d' }
    );
    refreshTokens.set(refreshToken, username);
    return reply.send({ token, refreshToken });
  });

  app.post('/auth/refresh', async (req, reply) => {
    const { refreshToken } = req.body as any;
    if (!refreshToken || !refreshTokens.has(refreshToken)) {
      return reply.code(401).send({ error: 'Invalid refresh token' });
    }
    try {
      const payload: any = await app.jwt.verify(refreshToken);
      refreshTokens.delete(refreshToken);
      const token = await reply.jwtSign({ username: payload.username });
      const newRefreshToken = await reply.jwtSign(
        { username: payload.username },
        { expiresIn: '7d' }
      );
      refreshTokens.set(newRefreshToken, payload.username);
      return reply.send({ token, refreshToken: newRefreshToken });
    } catch {
      return reply.code(401).send({ error: 'Invalid refresh token' });
    }
  });
}
