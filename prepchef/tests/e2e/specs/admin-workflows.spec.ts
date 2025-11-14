import { test } from '@playwright/test';
import { AuthPage } from '../pageObjects/auth';
import { AdminDashboardPage } from '../pageObjects/adminDashboard';
import { adminUser, hostUser } from '../fixtures/users';
import { demoKitchen } from '../fixtures/kitchens';
import { KitchenPayload, TestDataApiClient } from '../utils/testDataApi';

test.describe('Admin workflows', () => {
  let kitchenUnderReview: KitchenPayload;
  let hostAccount: typeof hostUser;

  test.beforeEach(async ({ page, request }, testInfo) => {
    const api = new TestDataApiClient(request);
    const uniqueSuffix = `${testInfo.workerIndex}-${Date.now()}`;

    hostAccount = {
      ...hostUser,
      email: `host+${uniqueSuffix}@prepchef.com`,
      name: `Host ${uniqueSuffix}`,
    };

    kitchenUnderReview = {
      ...demoKitchen,
      name: `${demoKitchen.name} ${uniqueSuffix}`,
      slug: `${demoKitchen.slug}-${uniqueSuffix}`,
    };

    await api.ensureUser(adminUser);
    await api.ensureUser(hostAccount);
    await api.seedKitchen(kitchenUnderReview, hostAccount.email);
    await api.createPendingCertification({
      kitchenSlug: kitchenUnderReview.slug,
      documentId: `cert-${uniqueSuffix}`,
      status: 'pending',
    });

    const authPage = new AuthPage(page);
    await authPage.goto('admin');
    await authPage.login(adminUser.email, adminUser.password);
    await authPage.expectSuccessfulLogin('/admin/dashboard');
  });

  test('admin can moderate kitchen listings', async ({ page }) => {
    const adminDashboard = new AdminDashboardPage(page);
    await adminDashboard.openModerationQueue();
    await adminDashboard.reviewPendingListing(kitchenUnderReview);
  });

  test('admin can approve certification documents', async ({ page, request }, testInfo) => {
    const adminDashboard = new AdminDashboardPage(page);
    const api = new TestDataApiClient(request);
    const additionalCertificationId = `cert-secondary-${testInfo.workerIndex}-${Date.now()}`;

    await api.createPendingCertification({
      kitchenSlug: kitchenUnderReview.slug,
      documentId: additionalCertificationId,
      status: 'pending',
    });

    await page.click('[data-testid="certifications-tab"]');
    await adminDashboard.approveCertification(additionalCertificationId);
  });

  test('admin can reject certification documents with a reason', async ({ page, request }, testInfo) => {
    const adminDashboard = new AdminDashboardPage(page);
    const api = new TestDataApiClient(request);
    const rejectionId = `cert-reject-${testInfo.workerIndex}-${Date.now()}`;

    await api.createPendingCertification({
      kitchenSlug: kitchenUnderReview.slug,
      documentId: rejectionId,
      status: 'pending',
    });

    await page.click('[data-testid="certifications-tab"]');
    await adminDashboard.rejectCertification(rejectionId, 'Missing updated inspection.');
  });

  test('admin can suspend a host account from the dashboard', async ({ page }) => {
    const adminDashboard = new AdminDashboardPage(page);
    await adminDashboard.suspendUser(hostAccount.email, 'Repeated policy violations.');
  });
});
