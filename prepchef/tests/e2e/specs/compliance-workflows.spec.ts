import { test } from '@playwright/test';
import { AuthPage } from '../pageObjects/auth';
import { ComplianceCenterPage } from '../pageObjects/complianceCenter';
import { adminUser, complianceOfficer, hostUser } from '../fixtures/users';
import { demoKitchen } from '../fixtures/kitchens';
import { KitchenPayload, TestDataApiClient } from '../utils/testDataApi';

test.describe('Compliance workflows', () => {
  let officerAccount: typeof complianceOfficer;
  let hostAccount: typeof hostUser;
  let kitchen: KitchenPayload;

  test.beforeEach(async ({ page, request }, testInfo) => {
    const api = new TestDataApiClient(request);
    const uniqueSuffix = `${testInfo.workerIndex}-${Date.now()}`;

    officerAccount = {
      ...complianceOfficer,
      email: `compliance+${uniqueSuffix}@prepchef.com`,
      name: `Compliance Officer ${uniqueSuffix}`,
    };

    hostAccount = {
      ...hostUser,
      email: `host-compliance+${uniqueSuffix}@prepchef.com`,
      name: `Compliance Host ${uniqueSuffix}`,
    };

    kitchen = {
      ...demoKitchen,
      name: `${demoKitchen.name} Compliance ${uniqueSuffix}`,
      slug: `${demoKitchen.slug}-compliance-${uniqueSuffix}`,
    };

    await api.ensureUser(officerAccount);
    await api.ensureUser(hostAccount);
    await api.ensureUser(adminUser);
    await api.seedKitchen(kitchen, hostAccount.email);

    const authPage = new AuthPage(page);
    await authPage.goto('compliance');
    await authPage.login(officerAccount.email, officerAccount.password);
    await authPage.expectSuccessfulLogin('/compliance/dashboard');
  });

  test('compliance officer can submit a new report', async ({ page }) => {
    const complianceCenter = new ComplianceCenterPage(page);

    await complianceCenter.gotoDashboard();
    await complianceCenter.submitReport({
      notes: 'Kitchen passes all safety checks.',
      score: 98,
    });
  });

  test('compliance officer can view the kitchen compliance badge', async ({ page, request }) => {
    const complianceCenter = new ComplianceCenterPage(page);
    const api = new TestDataApiClient(request);

    await api.submitComplianceReport({
      kitchenSlug: kitchen.slug,
      officerEmail: officerAccount.email,
      report: { notes: 'Badge ready', score: 100 },
    });

    await complianceCenter.gotoDashboard();
    await complianceCenter.viewComplianceBadge(kitchen.slug);
  });

  test('compliance officer can check certification status', async ({ page, request }) => {
    const complianceCenter = new ComplianceCenterPage(page);
    const api = new TestDataApiClient(request);

    await api.createPendingCertification({
      kitchenSlug: kitchen.slug,
      documentId: `cert-status-${Date.now()}`,
      status: 'approved',
    });

    await complianceCenter.gotoDashboard();
    await complianceCenter.checkCertificationStatus(kitchen.slug);
  });
});
