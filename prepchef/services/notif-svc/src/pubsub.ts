import EventEmitter from 'node:events';
import { log } from '@prep/logger';
import type { NotificationPubSub } from './types';

class LocalPubSub implements NotificationPubSub {
  private readonly emitter = new EventEmitter();

  async publish(channel: string, message: string): Promise<void> {
    this.emitter.emit(channel, message);
  }

  async subscribe(channel: string, handler: (message: string) => void): Promise<() => Promise<void>> {
    this.emitter.on(channel, handler);
    return async () => {
      this.emitter.off(channel, handler);
    };
  }

  async close(): Promise<void> {
    this.emitter.removeAllListeners();
  }
}

type RedisClient = {
  publish(channel: string, message: string): Promise<unknown>;
  subscribe(channel: string): Promise<unknown>;
  unsubscribe(channel: string): Promise<unknown>;
  quit(): Promise<unknown>;
  on(event: 'message' | 'error', handler: (...args: any[]) => void): void;
};

class RedisPubSub implements NotificationPubSub {
  private readonly publisher: RedisClient;
  private readonly subscriber: RedisClient;
  private readonly handlers = new Map<string, (message: string) => void>();

  constructor(publisher: RedisClient, subscriber: RedisClient) {
    this.publisher = publisher;
    this.subscriber = subscriber;
    this.subscriber.on('message', (channel, message) => {
      const handler = this.handlers.get(channel);
      if (handler) {
        handler(message);
      }
    });

    this.publisher.on('error', error => log.error('Redis publisher error', { error }));
    this.subscriber.on('error', error => log.error('Redis subscriber error', { error }));
  }

  async publish(channel: string, message: string): Promise<void> {
    await this.publisher.publish(channel, message);
  }

  async subscribe(channel: string, handler: (message: string) => void): Promise<() => Promise<void>> {
    this.handlers.set(channel, handler);
    await this.subscriber.subscribe(channel);
    return async () => {
      this.handlers.delete(channel);
      await this.subscriber.unsubscribe(channel);
    };
  }

  async close(): Promise<void> {
    await Promise.all([this.publisher.quit(), this.subscriber.quit()]);
  }
}

async function tryCreateRedisPubSub(url: string): Promise<NotificationPubSub | null> {
  try {
    const module = await import('ioredis');
    const RedisCtor = (module as any).default ?? (module as any);
    const options = { lazyConnect: true, maxRetriesPerRequest: 1, enableReadyCheck: false } as const;
    const publisher: RedisClient = new RedisCtor(url, options);
    const subscriber: RedisClient = new RedisCtor(url, options);
    return new RedisPubSub(publisher, subscriber);
  } catch (error) {
    log.warn('Redis module unavailable for notifications pub/sub', { error });
    return null;
  }
}

export async function createPubSub(): Promise<NotificationPubSub> {
  const redisUrl = process.env.REDIS_URL ?? process.env.REDIS_CONNECTION_STRING;
  if (!redisUrl) {
    return new LocalPubSub();
  }

  const redisPubSub = await tryCreateRedisPubSub(redisUrl);
  return redisPubSub ?? new LocalPubSub();
}
