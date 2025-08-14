import { FastifyInstance } from 'fastify';
import fastifyJwt from 'fastify-jwt';
import { z } from 'zod';

interface User {
  id: number;
  password: string;
}

const users = new Map<string, User>([[
  'demo',
  { id: 1, password: 'password' },
]]);

export const refreshTokens = new Map<string, number>();

export default async function (app: FastifyInstance) {
  app.register(fastifyJwt, {
    secret: process.env.JWT_SECRET || 'secret',
  });

  const credentialsSchema = z.object({
    username: z.string(),
    password: z.string(),
  });

  app.post('/auth/login', async (req, reply) => {
    const parsed = credentialsSchema.safeParse(req.body);
    if (!parsed.success) {
      return reply.code(400).send({ error: 'Invalid request' });
    }

    const { username, password } = parsed.data;
    const user = users.get(username);
    if (!user || user.password !== password) {
      return reply.code(401).send({ error: 'Invalid credentials' });
    }

    const token = app.jwt.sign({ sub: user.id }, { expiresIn: '15m' });
    const refreshToken = app.jwt.sign(
      { sub: user.id },
      { expiresIn: '7d' },
    );
    refreshTokens.set(refreshToken, user.id);

    return reply.send({ token, refreshToken });
  });

  const refreshSchema = z.object({ refreshToken: z.string() });

  app.post('/auth/refresh', async (req, reply) => {
    const parsed = refreshSchema.safeParse(req.body);
    if (!parsed.success) {
      return reply.code(400).send({ error: 'Invalid request' });
    }

    const { refreshToken } = parsed.data;
    if (!refreshTokens.has(refreshToken)) {
      return reply.code(401).send({ error: 'Invalid refresh token' });
    }

    try {
      const payload = app.jwt.verify<{ sub: number }>(refreshToken);
      const token = app.jwt.sign({ sub: payload.sub }, { expiresIn: '15m' });
      return reply.send({ token });
    } catch {
      return reply.code(401).send({ error: 'Invalid refresh token' });
    }
  });
}
