import { expect, test } from '@playwright/test';
import { AuthPage } from '../pageObjects/auth';
import { HostDashboardPage } from '../pageObjects/hostDashboard';
import { hostUser } from '../fixtures/users';
import { TestDataApiClient } from '../utils/testDataApi';

const TEST_REVENUE = 12850.75;
const TEST_SHIFTS = 9;
const TEST_INCIDENT_RATE = 0.12;

test.describe('Host analytics dashboard', () => {
  test('surfaces non-zero metrics sourced from mv_host_metrics', async ({ page, request }, testInfo) => {
    const api = new TestDataApiClient(request);
    const uniqueSuffix = `${testInfo.workerIndex}-${Date.now()}`;

    const hostAccount = {
      ...hostUser,
      email: `analytics-host+${uniqueSuffix}@prepchef.com`,
      name: `Analytics Host ${uniqueSuffix}`,
    };

    const hostProfile = await api.ensureUser(hostAccount);

    await api.seedHostMetrics({
      hostId: hostProfile.id,
      revenueLast30: TEST_REVENUE,
      shifts30: TEST_SHIFTS,
      incidentRate: TEST_INCIDENT_RATE,
    });

    const authPage = new AuthPage(page);
    await authPage.goto('host');
    await authPage.login(hostAccount.email, hostAccount.password);
    await authPage.expectSuccessfulLogin('/host/dashboard');

    const dashboard = new HostDashboardPage(page);
    await dashboard.gotoDashboard();
    await dashboard.openAnalytics();

    const metricsResponse = await page.request.get(`/analytics/host/${hostProfile.id}`);
    expect(metricsResponse.ok()).toBeTruthy();

    const metrics = (await metricsResponse.json()) as {
      revenue_last_30: number;
      shifts_30: number;
      incident_rate: number;
    };

    expect(metrics.revenue_last_30).toBeGreaterThan(0);
    expect(metrics.shifts_30).toBeGreaterThan(0);
    expect(metrics.incident_rate).toBeGreaterThanOrEqual(0);

    expect(metrics.revenue_last_30).toBeCloseTo(TEST_REVENUE, 2);
    expect(metrics.shifts_30).toBe(TEST_SHIFTS);

    const analyticsPanel = page.locator('[data-testid="analytics-dashboard"]');
    await expect(analyticsPanel).toBeVisible();

    const panelText = (await analyticsPanel.textContent()) ?? '';
    expect(panelText).toMatch(/\d/);
  });
});
