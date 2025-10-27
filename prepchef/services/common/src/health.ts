/**
 * Health Check Endpoints (G25)
 * Returns DB connectivity, Redis connectivity, and disk space
 */

import { FastifyInstance } from 'fastify';
import { Pool } from 'pg';
import Redis from 'ioredis';
import { execSync } from 'child_process';

export interface HealthStatus {
  ok: boolean;
  service: string;
  timestamp: string;
  checks: {
    database?: HealthCheck;
    redis?: HealthCheck;
    disk?: HealthCheck;
  };
}

export interface HealthCheck {
  status: 'healthy' | 'degraded' | 'unhealthy';
  latency_ms?: number;
  details?: any;
}

export async function registerHealthChecks(app: FastifyInstance, serviceName: string) {
  app.get('/health', async (req, reply) => {
    const health: HealthStatus = {
      ok: true,
      service: serviceName,
      timestamp: new Date().toISOString(),
      checks: {}
    };

    // Database check
    if (process.env.DATABASE_URL) {
      health.checks.database = await checkDatabase();
      if (health.checks.database.status === 'unhealthy') {
        health.ok = false;
      }
    }

    // Redis check
    if (process.env.REDIS_URL) {
      health.checks.redis = await checkRedis();
      if (health.checks.redis.status === 'unhealthy') {
        health.ok = false;
      }
    }

    // Disk check
    health.checks.disk = checkDisk();
    if (health.checks.disk.status === 'unhealthy') {
      health.ok = false;
    }

    const statusCode = health.ok ? 200 : 503;
    return reply.code(statusCode).send(health);
  });

  // Readiness check (for Kubernetes)
  app.get('/health/ready', async (req, reply) => {
    const dbOk = process.env.DATABASE_URL ? (await checkDatabase()).status !== 'unhealthy' : true;
    const redisOk = process.env.REDIS_URL ? (await checkRedis()).status !== 'unhealthy' : true;

    const ready = dbOk && redisOk;

    return reply.code(ready ? 200 : 503).send({
      ready,
      service: serviceName
    });
  });

  // Liveness check (for Kubernetes)
  app.get('/health/live', async (req, reply) => {
    return reply.code(200).send({
      alive: true,
      service: serviceName,
      uptime: process.uptime()
    });
  });
}

async function checkDatabase(): Promise<HealthCheck> {
  const db = new Pool({ connectionString: process.env.DATABASE_URL });

  try {
    const start = Date.now();
    await db.query('SELECT 1');
    const latency = Date.now() - start;

    await db.end();

    return {
      status: latency < 100 ? 'healthy' : 'degraded',
      latency_ms: latency
    };
  } catch (error) {
    await db.end();
    return {
      status: 'unhealthy',
      details: { error: (error as Error).message }
    };
  }
}

async function checkRedis(): Promise<HealthCheck> {
  const redis = new Redis(process.env.REDIS_URL || '');

  try {
    const start = Date.now();
    await redis.ping();
    const latency = Date.now() - start;

    await redis.quit();

    return {
      status: latency < 50 ? 'healthy' : 'degraded',
      latency_ms: latency
    };
  } catch (error) {
    await redis.quit();
    return {
      status: 'unhealthy',
      details: { error: (error as Error).message }
    };
  }
}

function checkDisk(): HealthCheck {
  try {
    const output = execSync('df -h / | tail -1').toString();
    const match = output.match(/(\d+)%/);
    const usagePercent = match ? parseInt(match[1]) : 0;

    return {
      status: usagePercent < 80 ? 'healthy' : usagePercent < 90 ? 'degraded' : 'unhealthy',
      details: {
        usage_percent: usagePercent,
        output: output.trim()
      }
    };
  } catch (error) {
    return {
      status: 'unhealthy',
      details: { error: (error as Error).message }
    };
  }
}
