import type { FastifyPluginAsync } from 'fastify';
import fastifyCors, { type FastifyCorsOptions } from '@fastify/cors';
import fastifyHelmet, { type FastifyHelmetOptions } from '@fastify/helmet';
import fastifyRateLimit, { type FastifyRateLimitOptions } from '@fastify/rate-limit';
import fastifyJwt, { type FastifyJWTOptions } from '@fastify/jwt';
import '@fastify/jwt';
import { log } from '@prep/logger';

type Falseable<T> = T | false | undefined;

export interface PrepSecurityPluginOptions {
  /**
   * Used for structured logging so requests can be traced back to a service.
   */
  serviceName: string;
  /** Optional overrides for CORS behaviour. Pass `false` to disable registration entirely. */
  cors?: Falseable<FastifyCorsOptions>;
  /** Optional overrides for Helmet configuration. Pass `false` to disable registration entirely. */
  helmet?: Falseable<FastifyHelmetOptions>;
  /** Optional overrides for rate limiting. Pass `false` to disable registration entirely. */
  rateLimit?: Falseable<FastifyRateLimitOptions>;
  /** Optional overrides for JWT configuration. Pass `false` to skip registering JWT. */
  jwt?: Falseable<FastifyJWTOptions>;
  /** Toggle the built-in request/response logging hooks. */
  requestLogging?: boolean;
}

interface TimedRequest {
  _prepStartAt?: bigint;
}

const defaultRateLimit: FastifyRateLimitOptions = {
  max: 120,
  timeWindow: '1 minute'
};

export const prepSecurityPlugin: FastifyPluginAsync<PrepSecurityPluginOptions> = async (
  app,
  options
) => {
  const {
    serviceName,
    cors = {},
    helmet = { contentSecurityPolicy: false },
    rateLimit = defaultRateLimit,
    jwt = {},
    requestLogging = true
  } = options;

  if (!serviceName) {
    throw new Error('prepSecurityPlugin requires a `serviceName` option');
  }

  if (cors !== false) {
    await app.register(fastifyCors, {
      origin: true,
      ...cors
    });
  }

  if (helmet !== false) {
    await app.register(fastifyHelmet, {
      contentSecurityPolicy: false,
      ...helmet
    });
  }

  if (rateLimit !== false) {
    await app.register(fastifyRateLimit, {
      ...defaultRateLimit,
      ...rateLimit
    });
  }

  if (jwt !== false) {
    const jwtOptions = (jwt || {}) as Partial<FastifyJWTOptions>;
    const secret = jwtOptions.secret;
    const { secret: _, ...rest } = jwtOptions;
    const jwtSecret = secret ?? process.env.JWT_SECRET;

    if (!jwtSecret) {
      throw new Error(
        'JWT_SECRET must be provided either via options.jwt.secret or JWT_SECRET environment variable. ' +
        'Never use default secrets in production.'
      );
    }

    await app.register(fastifyJwt, {
      secret: jwtSecret,
      ...rest
    });
  }

  if (requestLogging) {
    app.addHook('onRequest', async request => {
      (request as typeof request & TimedRequest)._prepStartAt = process.hrtime.bigint();
      log.info(`[${serviceName}] -> ${request.method} ${request.url}`, {
        requestId: request.id,
        ip: request.ip
      });
    });

    app.addHook('onResponse', async (request, reply) => {
      const start = (request as typeof request & TimedRequest)._prepStartAt;
      const duration = start ? Number((process.hrtime.bigint() - start) / BigInt(1e6)) : undefined;
      const durationMsg = duration !== undefined ? ` (${duration}ms)` : '';
      log.info(
        `[${serviceName}] <- ${request.method} ${request.url} ${reply.statusCode}${durationMsg}`,
        {
          requestId: request.id
        }
      );
    });
  }
};

export default prepSecurityPlugin;
