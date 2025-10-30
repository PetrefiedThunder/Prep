export type IntegrationStatus = 'active' | 'inactive' | 'error' | 'pending';

export interface Integration {
  id: string;
  userId: string;
  kitchenId?: string | null;
  serviceType: string;
  vendorName: string;
  authMethod: string;
  syncFrequency: string;
  status: IntegrationStatus;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface IntegrationInput {
  kitchenId?: string | null;
  serviceType: string;
  vendorName: string;
  authMethod: string;
  syncFrequency: string;
  status?: IntegrationStatus;
  metadata?: Record<string, unknown>;
}
