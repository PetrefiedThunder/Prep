import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import AdminModerationPage from '../pages/admin/moderation';

describe('AdminModerationPage', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    vi.restoreAllMocks();
    global.fetch = originalFetch;
  });

  it('renders pending certifications and submits an approval', async () => {
    const pendingResponse = {
      items: [
        {
          id: 'cert-1',
          kitchen_id: 'kitchen-1',
          kitchen_name: 'Sunset Bakery',
          document_type: 'Health permit',
          document_url: 'https://example.com/permit.pdf',
          status: 'pending',
          submitted_at: new Date('2024-01-10T12:00:00Z').toISOString(),
          verified_at: null,
          reviewer_id: null,
          rejection_reason: null,
          expires_at: null,
        },
      ],
      pagination: {
        limit: 10,
        offset: 0,
        total: 1,
      },
    };

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => pendingResponse })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ message: 'Certification approved' }) })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          items: [],
          pagination: { limit: 10, offset: 0, total: 0 },
        }),
      });

    global.fetch = fetchMock as unknown as typeof fetch;

    render(<AdminModerationPage />);

    await waitFor(() => expect(screen.getByText('Sunset Bakery')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /approve/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/admin/certifications/cert-1/verify',
        expect.objectContaining({ method: 'POST' }),
      ),
    );

    await waitFor(() => expect(screen.getByText('Certification approved')).toBeInTheDocument());
  });

  it('requires a rejection reason before rejecting a certification', async () => {
    const pendingResponse = {
      items: [
        {
          id: 'cert-2',
          kitchen_id: 'kitchen-2',
          kitchen_name: 'Harborview Kitchen',
          document_type: 'Fire inspection',
          document_url: 'https://example.com/fire.pdf',
          status: 'pending',
          submitted_at: new Date('2024-01-11T12:00:00Z').toISOString(),
          verified_at: null,
          reviewer_id: null,
          rejection_reason: null,
          expires_at: null,
        },
      ],
      pagination: {
        limit: 10,
        offset: 0,
        total: 1,
      },
    };

    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => pendingResponse });
    global.fetch = fetchMock as unknown as typeof fetch;

    render(<AdminModerationPage />);

    await waitFor(() => expect(screen.getByText('Harborview Kitchen')).toBeInTheDocument());

    await userEvent.click(screen.getByRole('button', { name: /reject/i }));

    expect(screen.getByText(/please provide a rejection reason/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
