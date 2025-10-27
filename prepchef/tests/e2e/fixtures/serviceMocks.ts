import { APIRequestContext, Page, Route } from '@playwright/test';

export interface DocuSignMock {
  envelopeId: string;
  signingUrl: string;
  triggerCompletion: () => Promise<void>;
}

export interface ComplianceStatusMock {
  setStatus: (status: 'pending' | 'submitted' | 'approved' | 'compliant') => void;
}

function respondJson(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function mockDocuSignEnvelope(page: Page): Promise<DocuSignMock> {
  const envelopeId = `env-${Date.now()}`;
  const signingUrl = `https://example.com/docusign/${envelopeId}`;
  let currentStatus: 'created' | 'completed' = 'created';

  await page.route('**/api/esignature/docusign/envelopes', async (route, request) => {
    if (request.method() === 'POST') {
      return respondJson(route, {
        envelopeId,
        signingUrl,
        status: currentStatus,
      }, 201);
    }

    return route.continue();
  });

  await page.route(`**/api/esignature/docusign/envelopes/${envelopeId}/status`, async route => {
    return respondJson(route, {
      envelopeId,
      status: currentStatus,
    });
  });

  return {
    envelopeId,
    signingUrl,
    async triggerCompletion() {
      currentStatus = 'completed';
      await page.evaluate(
        payload => {
          window.dispatchEvent(new CustomEvent('docusign:webhook', { detail: payload }));
        },
        { envelopeId, status: 'completed' }
      );
    },
  };
}

export async function mockComplianceStatus(
  page: Page,
  kitchenSlug: string
): Promise<ComplianceStatusMock> {
  let status: 'pending' | 'submitted' | 'approved' | 'compliant' = 'pending';

  await page.route('**/api/compliance/status**', async (route, request) => {
    if (request.method() === 'GET' && request.url().includes(kitchenSlug)) {
      return respondJson(route, {
        kitchenSlug,
        status,
      });
    }

    return route.continue();
  });

  return {
    setStatus(nextStatus) {
      status = nextStatus;
    },
  };
}

export async function sendDocuSignWebhook(
  request: APIRequestContext,
  payload: {
    envelopeId: string;
    kitchenSlug: string;
    signerEmail: string;
  }
) {
  try {
    await request.post('/api/test-data/webhooks/docusign', {
      data: {
        envelopeId: payload.envelopeId,
        kitchenSlug: payload.kitchenSlug,
        signerEmail: payload.signerEmail,
        status: 'completed',
      },
    });
  } catch (error) {
    console.warn('DocuSign webhook endpoint unavailable in test environment', error);
  }
}
