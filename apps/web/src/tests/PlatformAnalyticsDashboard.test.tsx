import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

import PlatformAnalyticsDashboard from '../components/analytics/PlatformAnalyticsDashboard';

type FetchArgs = Parameters<typeof fetch>;

type HookResult = {
  data: unknown;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
};

const mockUseHostMetrics = vi.fn<[], HookResult>();

vi.mock('../hooks/useHostMetrics', () => ({
  useHostMetrics: () => mockUseHostMetrics(),
}));

const originalFetch = globalThis.fetch;

const createJsonResponse = <T,>(payload: T): Response =>
  ({
    ok: true,
    json: async () => payload,
  } as unknown as Response);

beforeEach(() => {
  mockUseHostMetrics.mockReturnValue({
    data: {
      host_name: 'Harbor Kitchens',
      revenue_trend: [
        { date: '2024-03-01', value: 1000 },
        { date: '2024-03-02', value: 1200 },
      ],
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(async () => {}),
  });

  const fetchMock = vi.fn(async (...args: FetchArgs) => {
    const [input] = args;
    const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : '';

    if (url.endsWith('/analytics/platform/overview')) {
      return createJsonResponse({
        total_users: 1200,
        total_hosts: 180,
        total_kitchens: 220,
        active_kitchens: 190,
        total_bookings: 6400,
        total_revenue: '250000',
        new_users_last_30_days: 140,
        bookings_trend: [],
        revenue_trend: [],
      });
    }

    if (url.endsWith('/analytics/platform/revenue')) {
      return createJsonResponse({
        total_revenue: '250000',
        revenue_trends: [],
        revenue_by_kitchen: [],
        average_booking_value: '320',
        revenue_forecast: [],
        payment_methods_breakdown: [],
        top_hosts: [
          {
            host_id: '123',
            host_name: 'Harbor Kitchens',
            total_revenue: '120000',
          },
        ],
      });
    }

    if (url.endsWith('/analytics/platform/growth')) {
      return createJsonResponse({
        user_signups: [],
        host_signups: [],
        conversion_rate: [],
        acquisition_channels: [],
      });
    }

    if (url.endsWith('/analytics/admin/moderation')) {
      return createJsonResponse({
        pending: 0,
        in_review: 0,
        escalated: 0,
        sla_breaches: 0,
        average_review_time_hours: 0,
        moderation_trend: [],
      });
    }

    if (url.endsWith('/analytics/admin/performance')) {
      return createJsonResponse({
        total_resolved: 0,
        backlog: 0,
        productivity_trend: [],
        team: [],
      });
    }

    if (url.endsWith('/analytics/admin/financial')) {
      return createJsonResponse({
        total_revenue: '0',
        net_revenue: '0',
        operational_expenses: '0',
        gross_margin: 0,
        ebitda_margin: 0,
        cash_on_hand: '0',
        burn_rate: '0',
        runway_months: 0,
        revenue_trend: [],
        expense_trend: [],
      });
    }

    return createJsonResponse({});
  });

  globalThis.fetch = fetchMock as unknown as typeof fetch;
});

afterEach(() => {
  mockUseHostMetrics.mockReset();
  vi.restoreAllMocks();
  globalThis.fetch = originalFetch;
});

describe('PlatformAnalyticsDashboard', () => {
  it('renders the host revenue sparkline when top host data is available', async () => {
    render(<PlatformAnalyticsDashboard />);

    expect(await screen.findByText('Harbor Kitchens revenue')).toBeInTheDocument();
    expect(await screen.findByTestId('host-revenue-sparkline-chart')).toBeInTheDocument();
  });
});
