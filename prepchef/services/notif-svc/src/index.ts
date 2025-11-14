import Fastify, { type FastifyInstance, type FastifyReply, type FastifyRequest } from 'fastify';
import { log } from '@prep/logger';
import { prepSecurityPlugin } from '@prep/common';
import { z } from 'zod';
import { NotificationService } from './service';
import { InMemoryNotificationRepository } from './storage/in-memory-repository';
import { InMemoryPreferencesStore, DEFAULT_PREFERENCES } from './preferences';
import { SendGridEmailProvider } from './providers/email';
import { TwilioSmsProvider } from './providers/sms';
import { createPubSub } from './pubsub';
import type {
  NotificationChannel,
  NotificationPreferences,
  NotificationSendRequest,
  NotificationPubSub
} from './types';

interface NotificationContext {
  service: NotificationService;
  repository: InMemoryNotificationRepository;
  preferences: InMemoryPreferencesStore;
  emailProvider: SendGridEmailProvider;
  smsProvider: TwilioSmsProvider;
  pubsub: NotificationPubSub;
}

declare module 'fastify' {
  interface FastifyInstance {
    authenticate: (request: FastifyRequest, reply: FastifyReply) => Promise<void>;
    notificationContext: NotificationContext;
  }
}

declare module '@fastify/jwt' {
  interface FastifyJWT {
    user: {
      sub: string;
      email?: string;
      roles?: string[];
    };
  }
}

const updatePreferencesSchema = z
  .object({
    email: z.boolean().optional(),
    sms: z.boolean().optional(),
    push: z.boolean().optional(),
    in_app: z.boolean().optional()
  })
  .default({});

const sendNotificationSchema = z.object({
  type: z.string().min(1),
  title: z.string().min(1),
  body: z.string().min(1),
  recipient_id: z.string().min(1),
  data: z.record(z.any()).optional(),
  channels: z
    .array(z.enum(['email', 'sms', 'push', 'in_app']))
    .nonempty()
    .optional()
});

function toResponse(preferences: NotificationPreferences) {
  return {
    email: preferences.email,
    sms: preferences.sms,
    push: preferences.push,
    in_app: preferences.inApp
  };
}

function toSendRequest(input: z.infer<typeof sendNotificationSchema>): NotificationSendRequest {
  const baseChannels: NotificationChannel[] = ['email', 'push', 'in_app'];
  return {
    type: input.type,
    title: input.title,
    body: input.body,
    recipientId: input.recipient_id,
    data: input.data,
    channels: input.channels ?? baseChannels
  };
}

async function createNotificationContext(): Promise<NotificationContext> {
  const repository = new InMemoryNotificationRepository();
  const preferences = new InMemoryPreferencesStore();
  const emailProvider = new SendGridEmailProvider();
  const smsProvider = new TwilioSmsProvider();
  const pubsub = await createPubSub();
  const service = new NotificationService({
    repository,
    preferences,
    emailProvider,
    smsProvider,
    pubsub,
    heartbeatIntervalMs: 15000,
    heartbeatTimeoutMs: 45000
  });

  return { service, repository, preferences, emailProvider, smsProvider, pubsub };
}

export async function createApp(): Promise<FastifyInstance> {
  const app = Fastify({ logger: false });
  await app.register(prepSecurityPlugin, {
    serviceName: 'notif-svc'
  });

  const context = await createNotificationContext();
  app.decorate('notificationContext', context);

  app.decorate('authenticate', async (request: FastifyRequest, reply: FastifyReply) => {
    try {
      await request.jwtVerify();
    } catch (error) {
      return reply.code(401).send({ error: 'Unauthorized' });
    }
  });

  await context.service.register(app);
  await context.service.start();

  app.addHook('onClose', async () => {
    await context.service.stop();
    context.emailProvider.clear();
    context.smsProvider.clear();
    await context.repository.clear();
    context.preferences.clear();
  });

  app.get('/healthz', async () => ({ ok: true, svc: 'notif-svc' }));

  app.get('/api/v1/notifications/preferences', { preHandler: app.authenticate }, async request => {
    const userId = request.user.sub;
    const preferences = context.preferences.get(userId);
    return {
      user_id: userId,
      preferences: toResponse(preferences)
    };
  });

  app.put('/api/v1/notifications/preferences', { preHandler: app.authenticate }, async (request, reply) => {
    const body = updatePreferencesSchema.parse(request.body ?? {});
    const userId = request.user.sub;
    const existing = context.preferences.get(userId) ?? DEFAULT_PREFERENCES;
    const updated = context.preferences.merge(userId, {
      email: body.email ?? existing.email,
      sms: body.sms ?? existing.sms,
      push: body.push ?? existing.push,
      inApp: body.in_app ?? existing.inApp
    });

    return reply.send({
      user_id: userId,
      preferences: toResponse(updated)
    });
  });

  app.post('/api/v1/notifications/send', async (request, reply) => {
    const payload = toSendRequest(sendNotificationSchema.parse(request.body));
    const { record, channels } = await context.service.send(payload);
    return reply.code(202).send({
      notification_id: record.id,
      status: 'queued',
      channels,
      delivered_at: record.createdAt
    });
  });

  app.get('/api/v1/notifications', { preHandler: app.authenticate }, async request => {
    const userId = request.user.sub;
    const notifications = await context.repository.listForUser(userId);
    return {
      user_id: userId,
      notifications
    };
  });

  app.register(async function routes(instance) {
    instance.get('/', async () => ({ name: 'notif-svc' }));
  });

  return app;
}

if (require.main === module) {
  const port = Number(process.env.PORT || 0) || Math.floor(Math.random() * 1000) + 3000;
  createApp()
    .then(app =>
      app.listen({ port, host: '0.0.0.0' }).then(() => log.info('notif-svc listening', { port }))
    )
    .catch(error => {
      log.error('Failed to start notif-svc', { error });
      process.exitCode = 1;
    });
}

export type { NotificationContext };
