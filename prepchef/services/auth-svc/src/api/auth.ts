import { FastifyInstance } from 'fastify';
import '@fastify/jwt';
import bcrypt from 'bcryptjs';
import { z } from 'zod';
import { env } from '@prep/config';

type UserRole = 'admin' | 'host' | 'renter' | 'support';

const refreshTokens = new Map<string, string>();

const loginSchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1)
});

const refreshSchema = z.object({
  refreshToken: z.string().min(1)
});

const allowedRegistrationRoles: readonly UserRole[] = ['host', 'renter'];

const registerSchema = z.object({
  username: z.string().trim().min(3).max(64),
  email: z.string().trim().email(),
  fullName: z.string().trim().min(1).max(120),
  password: z.string().min(8).max(128),
  role: z
    .enum(allowedRegistrationRoles as [UserRole, ...UserRole[]])
    .default('renter')
    .optional()
});

type LoginBody = z.infer<typeof loginSchema>;
type RefreshBody = z.infer<typeof refreshSchema>;
type RegisterBody = z.infer<typeof registerSchema>;

function formatValidationError(error: z.ZodError) {
  return {
    error: 'Invalid request payload',
    details: error.flatten().fieldErrors
  };
}

function serialiseUser(user: { id: string; username: string; email: string; role: UserRole; verified: boolean }) {
  return {
    id: user.id,
    username: user.username,
    email: user.email,
    role: user.role,
    verified: user.verified
  };
}

export default async function (app: FastifyInstance) {
  app.post<{ Body: RegisterBody }>('/auth/register', async (req, reply) => {
    const parseResult = registerSchema.safeParse(req.body);
    if (!parseResult.success) {
      return reply.code(400).send(formatValidationError(parseResult.error));
    }

    const data = parseResult.data;

    const existingUsername = await app.userStore.findByUsername(data.username);
    if (existingUsername) {
      return reply.code(409).send({ error: 'Username is already taken' });
    }

    const existingEmail = await app.userStore.findByEmail(data.email);
    if (existingEmail) {
      return reply.code(409).send({ error: 'Email is already registered' });
    }

    const passwordHash = await bcrypt.hash(data.password, env.AUTH_PASSWORD_SALT_ROUNDS);
    const user = await app.userStore.createUser({
      username: data.username,
      email: data.email,
      fullName: data.fullName,
      passwordHash,
      role: data.role ?? 'renter'
    });

    const token = await reply.jwtSign(
      { sub: user.id, username: user.username, role: user.role },
      { expiresIn: env.AUTH_ACCESS_TOKEN_TTL }
    );
    const refreshToken = await reply.jwtSign(
      { sub: user.id, username: user.username, role: user.role, type: 'refresh', jti: randomUUID() },
      { expiresIn: env.AUTH_REFRESH_TOKEN_TTL }
    );
    refreshTokens.set(refreshToken, user.id);

    return reply.code(201).send({
      token,
      refreshToken,
      user: serialiseUser(user)
    });
  });

  app.post<{ Body: LoginBody }>('/auth/login', async (req, reply) => {
    const parseResult = loginSchema.safeParse(req.body);
    if (!parseResult.success) {
      return reply.code(400).send(formatValidationError(parseResult.error));
    }

    const { username, password } = parseResult.data;
    const user = await app.userStore.findByUsername(username);
    if (!user) {
      return reply.code(401).send({ error: 'Invalid credentials' });
    }

    const passwordValid = await bcrypt.compare(password, user.passwordHash);
    if (!passwordValid) {
      return reply.code(401).send({ error: 'Invalid credentials' });
    }

    const token = await reply.jwtSign(
      { sub: user.id, username: user.username, role: user.role },
      { expiresIn: env.AUTH_ACCESS_TOKEN_TTL }
    );
    const refreshToken = await reply.jwtSign(
      { sub: user.id, username: user.username, role: user.role, type: 'refresh', jti: randomUUID() },
      { expiresIn: env.AUTH_REFRESH_TOKEN_TTL }
    );
    refreshTokens.set(refreshToken, user.id);

    return reply.send({
      token,
      refreshToken,
      user: serialiseUser(user)
    });
  });

  app.post<{ Body: RefreshBody }>('/auth/refresh', async (req, reply) => {
    const parseResult = refreshSchema.safeParse(req.body);
    if (!parseResult.success) {
      return reply.code(400).send(formatValidationError(parseResult.error));
    }

    const { refreshToken } = parseResult.data;
    const storedUserId = refreshTokens.get(refreshToken);
    if (!storedUserId) {
      return reply.code(401).send({ error: 'Invalid refresh token' });
    }

    try {
      const payload = await app.jwt.verify<{
        sub: string;
        username: string;
        role: UserRole;
        type?: string;
      }>(refreshToken);
      if (payload.type !== 'refresh') {
        refreshTokens.delete(refreshToken);
        return reply.code(401).send({ error: 'Invalid refresh token' });
      }

      if (payload.sub !== storedUserId) {
        refreshTokens.delete(refreshToken);
        return reply.code(401).send({ error: 'Invalid refresh token' });
      }

      const user = await app.userStore.findByUsername(payload.username);
      if (!user) {
        refreshTokens.delete(refreshToken);
        return reply.code(401).send({ error: 'Invalid refresh token' });
      }

      refreshTokens.delete(refreshToken);

      const token = await reply.jwtSign(
        { sub: user.id, username: user.username, role: user.role },
        { expiresIn: env.AUTH_ACCESS_TOKEN_TTL }
      );
      const newRefreshToken = await reply.jwtSign(
        { sub: user.id, username: user.username, role: user.role, type: 'refresh', jti: randomUUID() },
        { expiresIn: env.AUTH_REFRESH_TOKEN_TTL }
      );
      refreshTokens.set(newRefreshToken, user.id);

      return reply.send({ token, refreshToken: newRefreshToken });
    } catch {
      refreshTokens.delete(refreshToken);
      return reply.code(401).send({ error: 'Invalid refresh token' });
    }
  });
}
