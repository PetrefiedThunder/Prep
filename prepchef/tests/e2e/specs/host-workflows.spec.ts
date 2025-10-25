import { test } from '@playwright/test';
import { resolve } from 'path';
import { AuthPage } from '../pageObjects/auth';
import { HostDashboardPage } from '../pageObjects/hostDashboard';
import { hostUser } from '../fixtures/users';
import { demoKitchen } from '../fixtures/kitchens';
import { KitchenPayload, TestDataApiClient } from '../utils/testDataApi';

const certificationFixturePath = resolve(__dirname, '../fixtures/files/health-certification.pdf');

test.describe('Host workflows', () => {
  let hostAccount: typeof hostUser;
  let kitchenDraft: KitchenPayload;

  test.beforeEach(async ({ page, request }, testInfo) => {
    const api = new TestDataApiClient(request);
    const uniqueSuffix = `${testInfo.workerIndex}-${Date.now()}`;

    hostAccount = {
      ...hostUser,
      email: `host-creator+${uniqueSuffix}@prepchef.com`,
      name: `Host Creator ${uniqueSuffix}`,
    };

    kitchenDraft = {
      ...demoKitchen,
      name: `${demoKitchen.name} Draft ${uniqueSuffix}`,
      slug: `${demoKitchen.slug}-draft-${uniqueSuffix}`,
    };

    await api.ensureUser(hostAccount);

    const authPage = new AuthPage(page);
    await authPage.goto('host');
    await authPage.login(hostAccount.email, hostAccount.password);
    await authPage.expectSuccessfulLogin('/host/dashboard');
  });

  test('host can create a kitchen listing', async ({ page }) => {
    const dashboard = new HostDashboardPage(page);
    await dashboard.gotoDashboard();
    await dashboard.startNewListing();
    await dashboard.fillListingForm(kitchenDraft);
    await dashboard.submitListing();
  });

  test('host can upload certification documentation', async ({ page, request }) => {
    const dashboard = new HostDashboardPage(page);
    const api = new TestDataApiClient(request);

    await api.seedKitchen(kitchenDraft, hostAccount.email);

    await dashboard.gotoDashboard();
    await dashboard.uploadCertification(certificationFixturePath);
  });

  test('host can view analytics dashboard', async ({ page, request }) => {
    const dashboard = new HostDashboardPage(page);
    const api = new TestDataApiClient(request);

    await api.seedKitchen(kitchenDraft, hostAccount.email);

    await dashboard.gotoDashboard();
    await dashboard.openAnalytics();
  });
});
