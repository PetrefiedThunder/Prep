import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import SFJoshuaTreeDemo from '../pages/SFJoshuaTreeDemo';
import type { FeesResponse, RequirementsResponse } from '../lib/prepTypes';

describe('SFJoshuaTreeDemo', () => {
  beforeEach(() => {
    vi.spyOn(global, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.includes('/city/san-francisco/fees')) {
        return Promise.resolve(new Response(JSON.stringify(mockFees('USD', 'san-francisco'))));
      }
      if (url.includes('/city/san-francisco/requirements')) {
        return Promise.resolve(new Response(JSON.stringify(mockRequirements('san-francisco'))));
      }
      if (url.includes('/city/joshua-tree/fees')) {
        return Promise.resolve(new Response(JSON.stringify(mockFees('USD', 'joshua-tree'))));
      }
      if (url.includes('/city/joshua-tree/requirements')) {
        return Promise.resolve(new Response(JSON.stringify(mockRequirements('joshua-tree'))));
      }
      return Promise.reject(new Error(`Unexpected request: ${url}`));
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders readiness information for both cities', async () => {
    render(<SFJoshuaTreeDemo />);

    await waitFor(() => {
      expect(screen.getByText('San Francisco, CA fees')).toBeInTheDocument();
      expect(screen.getByText('Joshua Tree, CA fees')).toBeInTheDocument();
    });

    expect(screen.getAllByText('Ready for launch')).toHaveLength(2);
    expect(screen.getAllByText('Health permit application')).toHaveLength(2);
    expect(screen.getAllByText('Environmental report')).toHaveLength(2);
  });
});

function mockFees(currency: string, city: string): FeesResponse {
  return {
    city,
    currency,
    totals: {
      one_time: 1200,
      recurring: 400,
      incremental: 150,
    },
    items: [
      {
        id: `${city}-1`,
        label: 'Permit application',
        amount: 1200,
        currency,
        kind: 'one_time',
      },
      {
        id: `${city}-2`,
        label: 'Inspection subscription',
        amount: 400,
        currency,
        kind: 'recurring',
      },
      {
        id: `${city}-3`,
        label: 'Per-delivery surcharge',
        amount: 150,
        currency,
        kind: 'incremental',
        unit: 'per delivery',
      },
    ],
    last_validated_at: new Date().toISOString(),
  };
}

function mockRequirements(city: string): RequirementsResponse {
  return {
    city,
    blocking_count: 0,
    counts_by_party: {
      operator: 3,
      platform: 2,
    },
    parties: [
      {
        party: 'operator',
        label: 'Kitchen operator',
        requirements: [
          {
            id: `${city}-req-1`,
            title: 'Health permit application',
            status: 'met',
            party: 'operator',
          },
          {
            id: `${city}-req-2`,
            title: 'Fire inspection',
            status: 'met',
            party: 'operator',
          },
        ],
      },
      {
        party: 'platform',
        label: 'Platform team',
        requirements: [
          {
            id: `${city}-req-3`,
            title: 'Environmental report',
            status: 'met',
            party: 'platform',
          },
        ],
      },
    ],
    change_candidates: [
      {
        id: `${city}-change-1`,
        title: 'Expedited inspection pilot',
        summary: 'Partner with local fire department for shared inspections.',
      },
    ],
    last_updated_at: new Date().toISOString(),
  };
}
