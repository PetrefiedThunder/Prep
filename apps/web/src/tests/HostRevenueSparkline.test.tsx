import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

import { HostRevenueSparkline } from '../components/analytics/HostRevenueSparkline';

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

beforeEach(() => {
  mockUseHostMetrics.mockReset();
});

describe('HostRevenueSparkline', () => {
  it('renders sparkline and aggregate metrics when data is available', () => {
    mockUseHostMetrics.mockReturnValue({
      data: {
        host_name: 'Marina Kitchens',
        revenue_trend: [
          { date: '2024-03-01', value: 1200 },
          { date: '2024-03-02', value: 1350 },
          { date: '2024-03-03', value: 1425 },
        ],
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(async () => {}),
    });

    render(<HostRevenueSparkline hostId="123" windowDays={3} currency="USD" locale="en-US" />);

    expect(screen.getByText('Marina Kitchens revenue')).toBeInTheDocument();
    expect(screen.getByTestId('host-revenue-total')).toHaveTextContent('$3,975');
    expect(screen.getByTestId('host-revenue-delta')).toHaveTextContent('+5.6%');
    expect(screen.getByTestId('host-revenue-sparkline-chart')).toBeInTheDocument();
  });

  it('shows loading placeholder while metrics are fetched', () => {
    mockUseHostMetrics.mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
      refetch: vi.fn(async () => {}),
    });

    render(<HostRevenueSparkline hostId="123" />);

    expect(screen.getByTestId('host-revenue-sparkline-loading')).toBeInTheDocument();
  });

  it('renders error banner if the hook reports an error', () => {
    mockUseHostMetrics.mockReturnValue({
      data: null,
      isLoading: false,
      error: 'Unable to load host metrics. Please try again later.',
      refetch: vi.fn(async () => {}),
    });

    render(<HostRevenueSparkline hostId="123" />);

    expect(
      screen.getByText('Unable to load host metrics. Please try again later.'),
    ).toBeInTheDocument();
  });

  it('renders empty state when there is no revenue activity', () => {
    mockUseHostMetrics.mockReturnValue({
      data: { revenue_trend: [] },
      isLoading: false,
      error: null,
      refetch: vi.fn(async () => {}),
    });

    render(<HostRevenueSparkline hostId="123" />);

    expect(screen.getByText('No revenue activity for this period.')).toBeInTheDocument();
  });
});
