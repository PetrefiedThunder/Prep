import { test } from '@playwright/test';
import { resolve } from 'path';
import { AuthPage } from '../pageObjects/auth';
import { HostDashboardPage } from '../pageObjects/hostDashboard';
import { HostOnboardingPage } from '../pageObjects/hostOnboarding';
import { hostUser } from '../fixtures/users';
import { demoKitchen } from '../fixtures/kitchens';
import { TestDataApiClient, KitchenPayload } from '../utils/testDataApi';
import {
  mockDocuSignEnvelope,
  mockComplianceStatus,
  sendDocuSignWebhook,
} from '../fixtures/serviceMocks';

const coiFixturePath = resolve(__dirname, '../fixtures/files/sample-coi.pdf');

test.describe('Host onboarding flow', () => {
  let hostAccount: typeof hostUser;
  let kitchenDraft: KitchenPayload;
  let envelopeId: string;
  let complianceMockHandle: Awaited<ReturnType<typeof mockComplianceStatus>>;
  let docuSignMockHandle: Awaited<ReturnType<typeof mockDocuSignEnvelope>>;

  test.beforeEach(async ({ page, request }, testInfo) => {
    const api = new TestDataApiClient(request);
    const uniqueSuffix = `${testInfo.workerIndex}-${Date.now()}`;

    hostAccount = {
      ...hostUser,
      email: `host-onboarding+${uniqueSuffix}@prepchef.com`,
      name: `Host Onboarding ${uniqueSuffix}`,
    };

    kitchenDraft = {
      ...demoKitchen,
      name: `${demoKitchen.name} Onboarding ${uniqueSuffix}`,
      slug: `${demoKitchen.slug}-onboarding-${uniqueSuffix}`,
    };

    await api.ensureUser(hostAccount);

    docuSignMockHandle = await mockDocuSignEnvelope(page);
    envelopeId = docuSignMockHandle.envelopeId;

    complianceMockHandle = await mockComplianceStatus(page, kitchenDraft.slug);

    const authPage = new AuthPage(page);
    await authPage.goto('host');
    await authPage.login(hostAccount.email, hostAccount.password);
    await authPage.expectSuccessfulLogin('/host/dashboard');
  });

  test('host can complete the onboarding checklist', async ({ page, request }) => {
    const dashboard = new HostDashboardPage(page);
    const onboarding = new HostOnboardingPage(page);
    const api = new TestDataApiClient(request);

    await dashboard.gotoDashboard();
    await dashboard.startNewListing();
    await dashboard.fillListingForm(kitchenDraft);
    await dashboard.submitListing();

    await onboarding.gotoChecklist();
    await onboarding.uploadCOI(coiFixturePath);

    await onboarding.launchDocuSign();
    await sendDocuSignWebhook(request, {
      envelopeId,
      kitchenSlug: kitchenDraft.slug,
      signerEmail: hostAccount.email,
    });

    await docuSignMockHandle.triggerCompletion();

    await onboarding.waitForDocuSignCompletion();

    complianceMockHandle.setStatus('compliant');

    await onboarding.refreshComplianceStatus();
    await onboarding.expectComplianceStatus('compliant');

    await api.createPendingCertification({
      kitchenSlug: kitchenDraft.slug,
      documentId: envelopeId,
      status: 'approved',
    });
  });
});
