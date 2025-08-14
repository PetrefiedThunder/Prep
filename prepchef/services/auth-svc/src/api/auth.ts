import { FastifyInstance } from 'fastify';
import fastifyJwt from '@fastify/jwt';

interface LoginBody {
  username: string;
  password: string;
}

interface RefreshBody {
  refreshToken: string;
}

/**
 * In-memory store for refresh tokens.
 * Map<refreshToken, username>
 * Replace with a durable store (DB/Redis) in production.
 */
const refreshTokens = new Map<string, string>();

export default async function authRoutes(app: FastifyInstance) {
  app.register(fastifyJwt, {
    secret: process.env.JWT_SECRET || 'supersecret',
  });

  app.post<{ Body: LoginBody }>('/auth/login', async (req, reply) => {
    const { username, password } = req.body;

    // TODO: replace with real user lookup + password hash verify
    if (username !== 'admin' || password !== 'secret') {
      return reply.code(401).send({ error: 'Invalid credentials' });
    }

    const token = await reply.jwtSign({ username }, { expiresIn: '15m' });
    const refreshToken = await reply.jwtSign(
      { username },
      { expiresIn: '7d' }
    );

    refreshTokens.set(refreshToken, username);

    return reply.send({ token, refreshToken });
  });

  app.post<{ Body: RefreshBody }>('/auth/refresh', async (req, reply) => {
    const { refreshToken } = req.body;

    if (!refreshToken || !refreshTokens.has(refreshToken)) {
      return reply.code(401).send({ error: 'Invalid refresh token' });
    }

    try {
      const payload = await app.jwt.verify<{ username: string }>(refreshToken);

      // Rotate the refresh token
      refreshTokens.delete(refreshToken);

      const token = await reply.jwtSign(
        { username: payload.username },
        { expiresIn: '15m' }
      );
      const newRefreshToken = await reply.jwtSign(
        { username: payload.username },
        { expiresIn: '7d' }
      );

      refreshTokens.set(newRefreshToken, payload.username);

      return reply.send({ token, refreshToken: newRefreshToken });
    } catch {
      // Token invalid/expired — revoke if present and reject
      refreshTokens.delete(refreshToken);
      return reply.code(401).send({ error: 'Invalid refresh token' });
    }
  });
}
