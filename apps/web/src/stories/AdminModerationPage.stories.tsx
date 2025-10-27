import { useEffect } from 'react';
import AdminModerationPage from '../pages/admin/moderation';

type MockResponse = {
  ok: true;
  json: () => Promise<unknown>;
};

function createResponse(data: unknown): MockResponse {
  return {
    ok: true,
    json: async () => data,
  };
}

function MockedAdminModerationPage() {
  useEffect(() => {
    const originalFetch = window.fetch;
    const pendingPayload = {
      items: [
        {
          id: 'cert-story-1',
          kitchen_id: 'story-kitchen-1',
          kitchen_name: 'Storybook Kitchen',
          document_type: 'Health permit',
          document_url: 'https://example.com/storybook.pdf',
          status: 'pending',
          submitted_at: new Date('2024-01-01T12:00:00Z').toISOString(),
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

    window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
      if (url.includes('/api/v1/admin/certifications/pending')) {
        return Promise.resolve(createResponse(pendingPayload));
      }
      if (url.includes('/api/v1/admin/certifications/') && init?.method === 'POST') {
        return Promise.resolve(createResponse({ message: 'Certification approved' }));
      }
      return originalFetch(input, init);
    };

    return () => {
      window.fetch = originalFetch;
    };
  }, []);

  return <AdminModerationPage />;
}

export default {
  title: 'Admin/ModerationPage',
  component: AdminModerationPage,
};

export const Default = () => <MockedAdminModerationPage />;
