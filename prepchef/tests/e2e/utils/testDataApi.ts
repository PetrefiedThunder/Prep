import { APIRequestContext, expect } from '@playwright/test';

export interface UserPayload {
  email: string;
  password: string;
  role: string;
  name: string;
}

export interface UserResponse {
  id: string;
  email: string;
  role: string;
  name: string;
}

export interface KitchenPayload {
  name: string;
  slug: string;
  address: string;
  capacity: number;
  equipment: string[];
  amenities: string[];
  hourlyRate: number;
  availability: {
    start: string;
    end: string;
  };
}

export interface CertificationPayload {
  kitchenSlug: string;
  documentId: string;
  status?: 'pending' | 'approved' | 'rejected';
}

export interface HostMetricsPayload {
  hostId: string;
  revenueLast30: number;
  shifts30: number;
  incidentRate: number;
}

export class TestDataApiClient {
  constructor(private readonly request: APIRequestContext) {}

  async ensureUser(user: UserPayload): Promise<UserResponse> {
    const response = await this.request.post('/api/test-data/users', {
      data: user,
    });

    expect(response.ok()).toBeTruthy();
    return response.json();
  }

  async seedKitchen(kitchen: KitchenPayload, ownerEmail: string) {
    const response = await this.request.post('/api/test-data/kitchens', {
      data: { ...kitchen, ownerEmail },
    });

    expect(response.ok()).toBeTruthy();
    return response.json();
  }

  async createPendingCertification(payload: CertificationPayload) {
    const response = await this.request.post('/api/test-data/certifications', {
      data: payload,
    });

    expect(response.ok()).toBeTruthy();
    return response.json();
  }

  async createBooking({
    kitchenSlug,
    renterEmail,
    start,
    end,
  }: {
    kitchenSlug: string;
    renterEmail: string;
    start: string;
    end: string;
  }) {
    const response = await this.request.post('/api/test-data/bookings', {
      data: {
        kitchenSlug,
        renterEmail,
        start,
        end,
      },
    });

    expect(response.ok()).toBeTruthy();
    return response.json();
  }

  async seedHostMetrics({ hostId, revenueLast30, shifts30, incidentRate }: HostMetricsPayload) {
    const response = await this.request.post('/api/test-data/host-metrics', {
      data: {
        host_id: hostId,
        revenue_last_30: revenueLast30,
        shifts_30: shifts30,
        incident_rate: incidentRate,
      },
    });

    expect(response.ok()).toBeTruthy();
    return response.json();
  }

  async submitComplianceReport({
    kitchenSlug,
    officerEmail,
    report,
  }: {
    kitchenSlug: string;
    officerEmail: string;
    report: Record<string, unknown>;
  }) {
    const response = await this.request.post('/api/test-data/compliance', {
      data: {
        kitchenSlug,
        officerEmail,
        report,
      },
    });

    expect(response.ok()).toBeTruthy();
    return response.json();
  }
}
