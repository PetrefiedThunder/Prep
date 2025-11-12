import { PrismaClient, type Prisma } from '@prisma/client';
import { env } from '@prep/config';

let prisma: PrismaClient | undefined;

function buildLoggingConfig(): ('info' | 'warn' | 'error' | 'query')[] {
  if (env.NODE_ENV === 'development') {
    return ['info', 'warn', 'error'];
  }

  if (env.NODE_ENV === 'test') {
    return ['warn', 'error'];
  }

  return ['error'];
}

export function getPrismaClient() {
  if (!prisma) {
    const log = buildLoggingConfig();
    prisma = new PrismaClient({
      log,
      datasources: env.DATABASE_URL
        ? {
            db: {
              url: env.DATABASE_URL
            }
          }
        : undefined
    });
  }

  return prisma;
}

export async function tryConnect() {
  if (!env.DATABASE_URL) {
    return false;
  }

  try {
    await getPrismaClient().$connect();
    return true;
  } catch {
    return false;
  }
}

export async function disconnectPrisma() {
  if (prisma) {
    await prisma.$disconnect();
    prisma = undefined;
  }
}

export type DatabaseClient = PrismaClient;
