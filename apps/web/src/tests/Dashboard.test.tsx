import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import Dashboard from '../pages/Dashboard';

const createResponse = (data: unknown, ok = true, status = 200) =>
  Promise.resolve({
    ok,
    status,
    json: () => Promise.resolve(data),
  }) as unknown as Response;

describe('Regulatory Dashboard', () => {
  beforeEach(() => {
    sessionStorage.clear();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.toString();
      const method = init?.method ?? 'GET';

      if (url.endsWith('/api/v1/regulatory/status') && method === 'GET') {
        return createResponse({
          overall_status: 'action_required',
          score: 87.5,
          last_updated: new Date().toISOString(),
          alerts_count: 1,
          pending_documents: 2,
        });
      }

      if (url.endsWith('/api/v1/regulatory/documents') && method === 'GET') {
        return createResponse([
          {
            id: 'occupancy-license',
            name: 'Commercial Occupancy License',
            status: 'pending',
            owner: 'admin',
            due_date: new Date().toISOString(),
          },
        ]);
      }

      if (url.endsWith('/api/v1/regulatory/history') && method === 'GET') {
        return createResponse({
          items: [
            {
              id: 'hist-001',
              occurred_at: new Date().toISOString(),
              actor: 'admin',
              description: 'Submitted test history entry.',
            },
          ],
          total: 1,
        });
      }

      if (url.endsWith('/api/v1/regulatory/monitoring/alerts') && method === 'GET') {
        return createResponse([
          {
            id: 'alert-1',
            created_at: new Date().toISOString(),
            severity: 'warning',
            message: 'Test alert',
            acknowledged: false,
          },
        ]);
      }

      if (url.endsWith('/api/v1/regulatory/monitoring/status') && method === 'GET') {
        return createResponse({
          last_run: new Date().toISOString(),
          healthy: true,
          active_alerts: 1,
        });
      }

      if (url.endsWith('/api/v1/regulatory/check') && method === 'POST') {
        return createResponse({
          status: 'completed',
          executed_at: new Date().toISOString(),
          report: { engine_version: '1.0.0' },
        });
      }

      if (url.endsWith('/api/v1/regulatory/monitoring/run') && method === 'POST') {
        return createResponse({
          last_run: new Date().toISOString(),
          healthy: true,
          active_alerts: 1,
        });
      }

      return createResponse({}, false, 404);
    });

    global.fetch = fetchMock as unknown as typeof fetch;
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it('renders compliance overview cards and documents', async () => {
    render(<Dashboard />);

    expect(
      await screen.findByRole('heading', {
        name: /Regulatory Compliance/i,
      }),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Commercial Occupancy License/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Compliance Score/i)).toBeInTheDocument();
    expect(screen.getByText(/Document Submission & Tracking/i)).toBeInTheDocument();
  });

  it('allows running automated compliance checks', async () => {
    render(<Dashboard />);

    const button = await screen.findByRole('button', { name: /Run compliance check/i });
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText(/Last check/i)).toBeInTheDocument();
      expect(screen.getByText(/Status: completed/i)).toBeInTheDocument();
    });
  });
});
