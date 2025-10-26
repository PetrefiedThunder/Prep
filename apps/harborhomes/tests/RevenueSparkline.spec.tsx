import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

import { RevenueSparkline } from '@/components/analytics/revenue-sparkline';

const mockUseHostMetrics = vi.fn();

vi.mock('@/hooks/use-host-metrics', () => ({
  useHostMetrics: (...args: unknown[]) => mockUseHostMetrics(...args),
}));

type MockMetric = {
  date: string;
  revenue: number;
  bookings: number;
  occupancy: number;
};

const createMetric = (overrides: Partial<MockMetric>): MockMetric => ({
  date: '2024-01-01',
  revenue: 0,
  bookings: 0,
  occupancy: 0,
  ...overrides,
});

beforeAll(() => {
  class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }

  // @ts-expect-error jsdom global augmentation
  global.ResizeObserver = ResizeObserver;
});

beforeEach(() => {
  mockUseHostMetrics.mockReset();
});

describe('RevenueSparkline', () => {
  it('renders revenue summary and delta with chart when data is available', () => {
    mockUseHostMetrics.mockReturnValue({
      metrics: [
        createMetric({ date: '2024-03-01', revenue: 1000 }),
        createMetric({ date: '2024-03-02', revenue: 1200 }),
        createMetric({ date: '2024-03-03', revenue: 1500 }),
      ],
      isLoading: false,
      error: null,
      isFallback: false,
      refreshedAt: new Date('2024-03-04T08:00:00Z'),
    });

    render(<RevenueSparkline days={3} currency="USD" locale="en-US" />);

    expect(screen.getByText('Revenue (last 3 days)')).toBeInTheDocument();
    expect(screen.getByText('$3,700')).toBeInTheDocument();
    expect(screen.getByText('+25.0% vs prev day')).toBeInTheDocument();
    expect(screen.getByTestId('revenue-sparkline-chart')).toBeInTheDocument();
  });

  it('renders loading skeleton while metrics are loading', () => {
    mockUseHostMetrics.mockReturnValue({
      metrics: [],
      isLoading: true,
      error: null,
      isFallback: false,
      refreshedAt: null,
    });

    render(<RevenueSparkline />);

    expect(screen.getByTestId('revenue-sparkline-skeleton')).toBeInTheDocument();
  });

  it('renders empty state message when there are no metrics', () => {
    mockUseHostMetrics.mockReturnValue({
      metrics: [],
      isLoading: false,
      error: null,
      isFallback: false,
      refreshedAt: null,
    });

    render(<RevenueSparkline />);

    expect(screen.getByText('No revenue data for this period.')).toBeInTheDocument();
  });

  it('announces fallback usage when simulated data is shown', () => {
    mockUseHostMetrics.mockReturnValue({
      metrics: [createMetric({ date: '2024-03-01', revenue: 1800 })],
      isLoading: false,
      error: 'Live metrics unavailable. Displaying simulated performance.',
      isFallback: true,
      refreshedAt: new Date('2024-03-02T00:00:00Z'),
    });

    render(<RevenueSparkline days={1} />);

    expect(
      screen.getByText('Showing simulated performance due to live data being unavailable.'),
    ).toBeInTheDocument();
  });
});
