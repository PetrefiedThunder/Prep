import { FastifyInstance } from 'fastify';
import '@fastify/jwt';

interface LoginBody {
  username: string;
  password: string;
}

interface RefreshBody {
  refreshToken: string;
}

// Allow simple configuration of demo credentials.
const VALID_USERNAME = process.env.AUTH_USERNAME || 'admin';
const VALID_PASSWORD = process.env.AUTH_PASSWORD || 'secret';

// In-memory persistence of refresh tokens. In a real service this
// would be swapped for a database or cache.
const refreshTokens = new Map<string, string>();

export default async function (app: FastifyInstance) {
  app.post<{ Body: LoginBody }>('/auth/login', async (req, reply) => {
    const { username, password } = req.body;
    if (username !== VALID_USERNAME || password !== VALID_PASSWORD) {
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

  app.post<{ Body: RefreshBody }>('/auth/refresh', async (req, reply) => {
    const { refreshToken } = req.body;
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
