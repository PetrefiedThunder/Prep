import type { FastifyRequest } from 'fastify';

export type NotificationChannel = 'email' | 'sms' | 'push' | 'in_app';

export interface NotificationSendRequest {
  type: string;
  title: string;
  body: string;
  recipientId: string;
  data?: Record<string, unknown>;
  channels?: NotificationChannel[];
}

export interface NotificationRecord {
  id: string;
  userId: string;
  type: string;
  title: string;
  body: string;
  data: Record<string, unknown>;
  createdAt: string;
  isRead: boolean;
  readAt?: string;
  emailSent: boolean;
  emailSentAt?: string;
  pushSent: boolean;
  pushSentAt?: string;
  smsSent: boolean;
  smsSentAt?: string;
}

export interface NotificationPreferences {
  email: boolean;
  sms: boolean;
  push: boolean;
  inApp: boolean;
}

export interface DeliveryReceipt {
  channel: NotificationChannel;
  delivered: boolean;
  detail?: string;
}

export interface NotificationRepository {
  create(record: Omit<NotificationRecord, 'createdAt' | 'isRead' | 'emailSent' | 'pushSent' | 'smsSent'>): Promise<NotificationRecord>;
  updateDelivery(id: string, patch: Partial<Pick<NotificationRecord, 'emailSent' | 'emailSentAt' | 'pushSent' | 'pushSentAt' | 'smsSent' | 'smsSentAt'>>): Promise<void>;
  listForUser(userId: string): Promise<NotificationRecord[]>;
  clear(): Promise<void>;
}

export interface NotificationPreferencesStore {
  get(userId: string): NotificationPreferences;
  set(userId: string, preferences: NotificationPreferences): void;
  merge(userId: string, patch: Partial<NotificationPreferences>): NotificationPreferences;
  clear(): void;
}

export interface EmailPayload {
  to: string;
  subject: string;
  text: string;
  html?: string;
  templateId?: string;
  data?: Record<string, unknown>;
}

export interface SmsPayload {
  to: string;
  body: string;
}

export interface EmailProvider {
  sendEmail(payload: EmailPayload): Promise<DeliveryReceipt>;
  getSentEmails(): EmailPayload[];
  clear(): void;
}

export interface SmsProvider {
  sendSms(payload: SmsPayload): Promise<DeliveryReceipt>;
  getSentMessages(): SmsPayload[];
  clear(): void;
}

export interface NotificationPubSub {
  publish(channel: string, message: string): Promise<void>;
  subscribe(channel: string, handler: (message: string) => void): Promise<() => Promise<void>>;
  close(): Promise<void>;
}

export interface AuthenticatedRequest extends FastifyRequest {
  user: {
    sub: string;
    email?: string;
    roles?: string[];
  };
}
