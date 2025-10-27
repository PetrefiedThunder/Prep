import { Page, expect } from '@playwright/test';

export class HostOnboardingPage {
  constructor(private readonly page: Page) {}

  async gotoChecklist() {
    await this.page.goto('/host/onboarding');
    await expect(this.page.locator('[data-testid="host-onboarding-checklist"]')).toBeVisible();
  }

  async uploadCOI(documentPath: string) {
    const fileChooserPromise = this.page.waitForEvent('filechooser');
    await this.page.click('[data-testid="coi-upload-button"]');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(documentPath);
    await expect(this.page.locator('[data-testid="coi-upload-success"]')).toContainText('COI uploaded');
  }

  async launchDocuSign() {
    await this.page.click('[data-testid="launch-docusign"]');
    await expect(this.page.locator('[data-testid="docusign-status"]')).toContainText('Envelope created');
  }

  async waitForDocuSignCompletion() {
    await expect(this.page.locator('[data-testid="docusign-status"]')).toContainText(/completed/i);
  }

  async refreshComplianceStatus() {
    await this.page.click('[data-testid="refresh-compliance-status"]');
  }

  async expectComplianceStatus(expected: string) {
    await expect(this.page.locator('[data-testid="compliance-status-value"]')).toContainText(expected);
  }
}
