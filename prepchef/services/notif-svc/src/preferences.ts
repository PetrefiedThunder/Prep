import { cloneDeep } from './utils/clone';
import type { NotificationPreferences, NotificationPreferencesStore } from './types';

const DEFAULT_PREFERENCES: NotificationPreferences = {
  email: true,
  sms: false,
  push: true,
  inApp: true
};

export class InMemoryPreferencesStore implements NotificationPreferencesStore {
  private store = new Map<string, NotificationPreferences>();

  get(userId: string): NotificationPreferences {
    const existing = this.store.get(userId);
    if (!existing) {
      return { ...DEFAULT_PREFERENCES };
    }
    return cloneDeep(existing);
  }

  set(userId: string, preferences: NotificationPreferences): void {
    this.store.set(userId, { ...DEFAULT_PREFERENCES, ...preferences });
  }

  merge(userId: string, patch: Partial<NotificationPreferences>): NotificationPreferences {
    const merged = { ...DEFAULT_PREFERENCES, ...this.store.get(userId), ...patch };
    this.store.set(userId, merged);
    return cloneDeep(merged);
  }

  clear(): void {
    this.store.clear();
  }
}

export { DEFAULT_PREFERENCES };
