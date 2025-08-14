import { FastifyInstance } from 'fastify';
import fastifyJwt from 'fastify-jwt';

declare module 'fastify' {
  interface FastifyInstance {
    refreshTokens: Set<string>;
  }
}

export default async function (app: FastifyInstance) {
  app.register(fastifyJwt, { secret: 'supersecret' });
  app.decorate('refreshTokens', new Set<string>());

  app.post('/auth/login', async (req, reply) => {
    const { username, password } = req.body as any;
    if (username !== 'user' || password !== 'pass') {
      return reply.code(401).send({ error: 'invalid credentials' });
    }

    const token = app.jwt.sign({ username }, { expiresIn: '15m' });
    const refreshToken = app.jwt.sign({ username }, { expiresIn: '7d' });
    app.refreshTokens.add(refreshToken);

    return reply.send({ token, refreshToken });
  });

  app.post('/auth/refresh', async (req, reply) => {
    const { refreshToken } = req.body as any;
    if (!refreshToken || !app.refreshTokens.has(refreshToken)) {
      return reply.code(401).send({ error: 'invalid refresh token' });
    }

    try {
      const payload = app.jwt.verify(refreshToken) as any;
      app.refreshTokens.delete(refreshToken);
      const token = app.jwt.sign({ username: payload.username }, { expiresIn: '15m' });
      const newRefreshToken = app.jwt.sign({ username: payload.username }, { expiresIn: '7d' });
      app.refreshTokens.add(newRefreshToken);
      return reply.send({ token, refreshToken: newRefreshToken });
    } catch {
      app.refreshTokens.delete(refreshToken);
      return reply.code(401).send({ error: 'invalid refresh token' });
    }
  });
}
