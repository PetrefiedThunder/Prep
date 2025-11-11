import { z } from 'zod';

type PersistenceMode = 'database' | 'memory';

const databaseUrlSchema = z
  .string()
  .min(1, 'DATABASE_URL must not be empty')
  .regex(/^postgres(ql)?:\/\//, {
    message: 'DATABASE_URL must be a PostgreSQL connection string'
  });

const envSchema = z.object({
  NODE_ENV: z
    .enum(['development', 'test', 'production'])
    .default('development'),
  DATABASE_URL: databaseUrlSchema.optional(),
  JWT_SECRET: z.string().min(32, 'JWT_SECRET must be at least 32 characters for security'),
  AUTH_PERSISTENCE: z
    .enum(['database', 'memory'])
    .default(process.env.NODE_ENV === 'test' ? 'memory' : 'database'),
  AUTH_PASSWORD_SALT_ROUNDS: z
    .coerce.number()
    .int()
    .min(4)
    .max(15)
    .default(10),
  AUTH_ACCESS_TOKEN_TTL: z.string().default('15m'),
  AUTH_REFRESH_TOKEN_TTL: z.string().default('7d'),
  AUTH_DEMO_USERNAME: z.string().min(1).default('admin'),
  AUTH_DEMO_PASSWORD: z.string().min(1).default('secret'),
  AUTH_DEMO_EMAIL: z.string().email().default('admin@prepchef.test')
});

export type PrepEnv = z.infer<typeof envSchema> & { AUTH_PERSISTENCE: PersistenceMode };

let cachedEnv: PrepEnv | undefined;

export function loadEnv(overrides?: Partial<Record<keyof PrepEnv, string | number>>) {
  if (!cachedEnv || overrides) {
    const parsed = envSchema.parse({
      NODE_ENV: overrides?.NODE_ENV ?? process.env.NODE_ENV,
      DATABASE_URL: overrides?.DATABASE_URL ?? process.env.DATABASE_URL,
      JWT_SECRET: overrides?.JWT_SECRET ?? process.env.JWT_SECRET,
      AUTH_PERSISTENCE:
        overrides?.AUTH_PERSISTENCE ?? (process.env.AUTH_PERSISTENCE as PersistenceMode | undefined),
      AUTH_PASSWORD_SALT_ROUNDS:
        overrides?.AUTH_PASSWORD_SALT_ROUNDS ?? process.env.AUTH_PASSWORD_SALT_ROUNDS,
      AUTH_ACCESS_TOKEN_TTL:
        overrides?.AUTH_ACCESS_TOKEN_TTL ?? process.env.AUTH_ACCESS_TOKEN_TTL,
      AUTH_REFRESH_TOKEN_TTL:
        overrides?.AUTH_REFRESH_TOKEN_TTL ?? process.env.AUTH_REFRESH_TOKEN_TTL,
      AUTH_DEMO_USERNAME: overrides?.AUTH_DEMO_USERNAME ?? process.env.AUTH_DEMO_USERNAME,
      AUTH_DEMO_PASSWORD: overrides?.AUTH_DEMO_PASSWORD ?? process.env.AUTH_DEMO_PASSWORD,
      AUTH_DEMO_EMAIL: overrides?.AUTH_DEMO_EMAIL ?? process.env.AUTH_DEMO_EMAIL
    });

    cachedEnv = parsed as PrepEnv;
  }

  return cachedEnv;
}

export const env = loadEnv();

export function resetEnvCache() {
  cachedEnv = undefined;
}

export const isDatabaseEnabled = () => env.AUTH_PERSISTENCE === 'database' && Boolean(env.DATABASE_URL);
