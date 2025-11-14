import crypto from 'node:crypto';
import { cloneDeep } from '../utils/clone';
import type { NotificationRecord, NotificationRepository } from '../types';

export class InMemoryNotificationRepository implements NotificationRepository {
  private notifications: NotificationRecord[] = [];

  async create(
    record: Omit<NotificationRecord, 'createdAt' | 'isRead' | 'emailSent' | 'pushSent' | 'smsSent'>
  ): Promise<NotificationRecord> {
    const notification: NotificationRecord = {
      id: record.id ?? crypto.randomUUID(),
      userId: record.userId,
      type: record.type,
      title: record.title,
      body: record.body,
      data: record.data ?? {},
      createdAt: new Date().toISOString(),
      isRead: false,
      readAt: record.readAt,
      emailSent: false,
      emailSentAt: undefined,
      pushSent: false,
      pushSentAt: undefined,
      smsSent: false,
      smsSentAt: undefined
    };

    this.notifications.push(notification);
    return cloneDeep(notification);
  }

  async updateDelivery(
    id: string,
    patch: Partial<Pick<NotificationRecord, 'emailSent' | 'emailSentAt' | 'pushSent' | 'pushSentAt' | 'smsSent' | 'smsSentAt'>>
  ): Promise<void> {
    const target = this.notifications.find(item => item.id === id);
    if (!target) {
      return;
    }

    Object.assign(target, patch);
  }

  async listForUser(userId: string): Promise<NotificationRecord[]> {
    return this.notifications.filter(item => item.userId === userId).map(notification => cloneDeep(notification));
  }

  async clear(): Promise<void> {
    this.notifications = [];
  }
}
