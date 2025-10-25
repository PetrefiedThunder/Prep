import crypto from 'node:crypto';
import type { FastifyInstance } from 'fastify';
import websocket from '@fastify/websocket';
import type { SocketStream } from '@fastify/websocket';
import { log } from '@prep/logger';
import type {
  DeliveryReceipt,
  EmailProvider,
  NotificationChannel,
  NotificationPreferencesStore,
  NotificationPubSub,
  NotificationRecord,
  NotificationRepository,
  NotificationSendRequest,
  SmsProvider
} from './types';

interface WebSocketClient {
  id: string;
  userId: string;
  connection: SocketStream;
  lastHeartbeat: number;
}

export interface NotificationServiceOptions {
  repository: NotificationRepository;
  preferences: NotificationPreferencesStore;
  emailProvider: EmailProvider;
  smsProvider: SmsProvider;
  pubsub: NotificationPubSub;
  heartbeatIntervalMs?: number;
  heartbeatTimeoutMs?: number;
}

interface PubSubNotificationPayload {
  originId: string;
  notification: NotificationRecord;
}

export class NotificationService {
  private readonly clients = new Map<string, Map<string, WebSocketClient>>();
  private readonly instanceId = crypto.randomUUID();
  private heartbeatTimer?: NodeJS.Timeout;
  private unsubscribe?: () => Promise<void>;

  constructor(private readonly options: NotificationServiceOptions) {}

  async register(app: FastifyInstance): Promise<void> {
    await app.register(websocket, { options: { maxPayload: 1048576 } });

    app.get('/ws', { websocket: true }, (connection, request) => {
      const tokenParam = new URL(request.url || '/', 'http://localhost').searchParams.get('token');
      const authHeader = request.headers['authorization'];
      const bearerToken = Array.isArray(authHeader)
        ? authHeader[0]
        : authHeader?.split(' ')[0]?.toLowerCase() === 'bearer'
          ? authHeader.split(' ')[1]
          : undefined;
      const userId =
        (request as any).user?.sub ??
        this.decodeToken(app, bearerToken ?? tokenParam);
      if (!userId) {
        connection.socket.close(4401, 'Unauthorized');
        return;
      }

      const clientId = crypto.randomUUID();
      const now = Date.now();
      const client: WebSocketClient = {
        id: clientId,
        userId,
        connection,
        lastHeartbeat: now
      };

      const userClients = this.clients.get(userId) ?? new Map<string, WebSocketClient>();
      userClients.set(clientId, client);
      this.clients.set(userId, userClients);

      connection.socket.on('message', data => {
        try {
          const parsed = JSON.parse(data.toString());
          if (parsed.type === 'pong') {
            client.lastHeartbeat = Date.now();
          }
        } catch (error) {
          log.warn('Failed to parse websocket message', { error });
        }
      });

      connection.socket.on('pong', () => {
        client.lastHeartbeat = Date.now();
      });

      connection.socket.on('close', () => {
        userClients.delete(clientId);
        if (userClients.size === 0) {
          this.clients.delete(userId);
        }
      });

      connection.socket.send(
        JSON.stringify({
          type: 'connected',
          clientId,
          userId,
          heartbeatIntervalMs: this.options.heartbeatIntervalMs ?? 30000
        })
      );
    });
  }

  private decodeToken(app: FastifyInstance, token: string | null): string | undefined {
    if (!token) {
      return undefined;
    }
    try {
      const decoded = app.jwt.verify(token) as { sub?: string };
      return decoded?.sub;
    } catch (error) {
      log.warn('Failed to verify websocket token', { error });
      return undefined;
    }
  }

  async start(): Promise<void> {
    this.unsubscribe = await this.options.pubsub.subscribe('notifications', message => {
      try {
        const payload = JSON.parse(message) as PubSubNotificationPayload;
        if (payload.originId === this.instanceId) {
          return;
        }
        this.broadcast(payload.notification);
      } catch (error) {
        log.error('Failed to process notification from pub/sub', { error });
      }
    });

    const interval = this.options.heartbeatIntervalMs ?? 30000;
    this.heartbeatTimer = setInterval(() => this.runHeartbeat(), interval).unref();
  }

  async stop(): Promise<void> {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
    }

    if (this.unsubscribe) {
      await this.unsubscribe();
    }

    await this.options.pubsub.close();

    for (const [, userClients] of this.clients) {
      for (const [, client] of userClients) {
        client.connection.socket.terminate();
      }
    }

    this.clients.clear();
  }

  async send(notification: NotificationSendRequest): Promise<{
    record: NotificationRecord;
    channels: NotificationChannel[];
  }> {
    const preferences = this.options.preferences.get(notification.recipientId);
    const requestedChannels = notification.channels ?? ['email', 'push', 'in_app'];
    const allowedChannels = this.filterChannels(requestedChannels, preferences);

    const record = await this.options.repository.create({
      id: crypto.randomUUID(),
      userId: notification.recipientId,
      type: notification.type,
      title: notification.title,
      body: notification.body,
      data: notification.data ?? {},
      readAt: undefined,
      emailSentAt: undefined,
      pushSentAt: undefined,
      smsSentAt: undefined
    });

    const deliveries: Promise<DeliveryReceipt>[] = [];

    if (allowedChannels.includes('email')) {
      deliveries.push(
        this.options.emailProvider
          .sendEmail({
            to: notification.recipientId,
            subject: notification.title,
            text: notification.body,
            data: notification.data
          })
          .then(receipt => {
            if (receipt.delivered) {
              const timestamp = new Date().toISOString();
              record.emailSent = true;
              record.emailSentAt = timestamp;
              void this.options.repository.updateDelivery(record.id, {
                emailSent: true,
                emailSentAt: timestamp
              });
            }
            return receipt;
          })
      );
    }

    if (allowedChannels.includes('sms')) {
      deliveries.push(
        this.options.smsProvider
          .sendSms({
            to: notification.recipientId,
            body: notification.body
          })
          .then(receipt => {
            if (receipt.delivered) {
              const timestamp = new Date().toISOString();
              record.smsSent = true;
              record.smsSentAt = timestamp;
              void this.options.repository.updateDelivery(record.id, {
                smsSent: true,
                smsSentAt: timestamp
              });
            }
            return receipt;
          })
      );
    }

    if (allowedChannels.includes('push') || allowedChannels.includes('in_app')) {
      const timestamp = new Date().toISOString();
      record.pushSent = true;
      record.pushSentAt = timestamp;
      void this.options.repository.updateDelivery(record.id, {
        pushSent: true,
        pushSentAt: timestamp
      });
      this.broadcast(record);
    }

    await Promise.allSettled(deliveries);

    await this.options.pubsub.publish(
      'notifications',
      JSON.stringify({ originId: this.instanceId, notification: record })
    );

    return { record, channels: allowedChannels };
  }

  private broadcast(notification: NotificationRecord): void {
    const clients = this.clients.get(notification.userId);
    if (!clients) {
      return;
    }

    const payload = JSON.stringify({ type: 'notification', notification });
    for (const [, client] of clients) {
      try {
        client.connection.socket.send(payload);
      } catch (error) {
        log.warn('Failed to deliver notification via websocket', { error });
      }
    }
  }

  private filterChannels(channels: NotificationChannel[], preferences: { [K in NotificationChannel]?: boolean }): NotificationChannel[] {
    const allowed: NotificationChannel[] = [];
    for (const channel of channels) {
      if (channel === 'in_app') {
        if (preferences.inApp !== false) {
          allowed.push(channel);
        }
      } else if (preferences[channel] !== false) {
        allowed.push(channel);
      }
    }
    return [...new Set(allowed)];
  }

  private runHeartbeat(): void {
    const timeout = this.options.heartbeatTimeoutMs ?? (this.options.heartbeatIntervalMs ?? 30000) * 2;
    const now = Date.now();

    for (const [userId, clients] of this.clients) {
      for (const [clientId, client] of clients) {
        if (now - client.lastHeartbeat > timeout) {
          log.warn('Closing stale websocket client', { userId, clientId });
          client.connection.socket.terminate();
          clients.delete(clientId);
          continue;
        }

        try {
          client.connection.socket.ping();
        } catch (error) {
          log.warn('Failed to send heartbeat ping', { userId, clientId, error });
        }
      }

      if (clients.size === 0) {
        this.clients.delete(userId);
      }
    }
  }
}
