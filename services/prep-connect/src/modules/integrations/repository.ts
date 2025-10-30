import { randomUUID } from 'node:crypto';

import type { Integration, IntegrationInput } from './types';

function nowIso(): string {
  return new Date().toISOString();
}

class IntegrationRepository {
  private readonly store = new Map<string, Integration>();

  listByUser(userId: string): Integration[] {
    return Array.from(this.store.values()).filter((integration) => integration.userId === userId);
  }

  get(id: string): Integration | undefined {
    return this.store.get(id);
  }

  create(userId: string, input: IntegrationInput): Integration {
    const id = randomUUID();
    const timestamp = nowIso();
    const integration: Integration = {
      id,
      userId,
      kitchenId: input.kitchenId ?? null,
      serviceType: input.serviceType,
      vendorName: input.vendorName,
      authMethod: input.authMethod,
      syncFrequency: input.syncFrequency,
      status: input.status ?? 'active',
      metadata: input.metadata ?? {},
      createdAt: timestamp,
      updatedAt: timestamp,
    };
    this.store.set(id, integration);
    return integration;
  }

  update(id: string, input: IntegrationInput): Integration | undefined {
    const existing = this.store.get(id);
    if (!existing) {
      return undefined;
    }
    const updated: Integration = {
      ...existing,
      ...input,
      metadata: input.metadata ?? existing.metadata,
      kitchenId: input.kitchenId ?? existing.kitchenId ?? null,
      status: input.status ?? existing.status,
      updatedAt: nowIso(),
    };
    this.store.set(id, updated);
    return updated;
  }

  delete(id: string): boolean {
    return this.store.delete(id);
  }
}

export const integrations = new IntegrationRepository();
