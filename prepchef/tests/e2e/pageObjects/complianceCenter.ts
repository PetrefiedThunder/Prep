import { Page, expect } from '@playwright/test';

export class ComplianceCenterPage {
  constructor(private readonly page: Page) {}

  async gotoDashboard() {
    await this.page.goto('/compliance/dashboard');
    await expect(this.page.locator('[data-testid="compliance-dashboard"]')).toBeVisible();
  }

  async submitReport(report: Record<string, unknown>) {
    await this.page.click('[data-testid="submit-report"]');
    await expect(this.page.locator('[data-testid="compliance-form"]')).toBeVisible();
    await this.page.fill('[data-testid="inspection-notes"]', String(report.notes ?? 'All good'));
    await this.page.fill('[data-testid="inspection-score"]', String(report.score ?? 100));
    await this.page.click('[data-testid="compliance-submit"]');
    await expect(this.page.locator('[role="status"]')).toContainText('Compliance report submitted');
  }

  async viewComplianceBadge(kitchenSlug: string) {
    await this.page.fill('[data-testid="badge-search"]', kitchenSlug);
    await this.page.click('[data-testid="badge-search-submit"]');
    await expect(this.page.locator('[data-testid="compliance-badge"]')).toBeVisible();
  }

  async checkCertificationStatus(kitchenSlug: string) {
    await this.page.click('[data-testid="certification-status-tab"]');
    await this.page.fill('[data-testid="certification-search"]', kitchenSlug);
    await this.page.click('[data-testid="certification-search-submit"]');
    await expect(this.page.locator(`[data-testid="certification-status-${kitchenSlug}"]`)).toBeVisible();
  }
}
