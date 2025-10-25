import { Page, expect } from '@playwright/test';
import { KitchenPayload } from '../utils/testDataApi';

export class AdminDashboardPage {
  constructor(private readonly page: Page) {}

  async openModerationQueue() {
    await this.page.click('[data-testid="moderation-queue-tab"]');
    await expect(this.page.locator('[data-testid="moderation-queue"]')).toBeVisible();
  }

  async reviewPendingListing(kitchen: KitchenPayload) {
    await this.page.click(`[data-testid="listing-card-${kitchen.slug}"]`);
    await expect(this.page.locator('[data-testid="listing-detail"]')).toContainText(
      kitchen.name,
    );
    await this.page.click('[data-testid="approve-listing"]');
    await expect(this.page.locator('[role="status"]')).toContainText('Listing approved');
  }

  async rejectCertification(documentId: string, reason: string) {
    await this.page.click(`[data-testid="certification-${documentId}"]`);
    await expect(this.page.locator('[data-testid="certification-modal"]')).toBeVisible();
    await this.page.fill('[data-testid="certification-rejection-reason"]', reason);
    await this.page.click('[data-testid="reject-certification"]');
    await expect(this.page.locator('[role="status"]')).toContainText('Certification rejected');
  }

  async approveCertification(documentId: string) {
    await this.page.click(`[data-testid="certification-${documentId}"]`);
    await expect(this.page.locator('[data-testid="certification-modal"]')).toBeVisible();
    await this.page.click('[data-testid="approve-certification"]');
    await expect(this.page.locator('[role="status"]')).toContainText('Certification approved');
  }

  async suspendUser(email: string, reason: string) {
    await this.page.click('[data-testid="user-management-tab"]');
    await this.page.fill('[data-testid="user-search"]', email);
    await this.page.click('[data-testid="user-search-submit"]');
    await expect(this.page.locator(`[data-testid="user-row-${email}"]`)).toBeVisible();
    await this.page.click(`[data-testid="suspend-user-${email}"]`);
    await this.page.fill('[data-testid="suspension-reason"]', reason);
    await this.page.click('[data-testid="confirm-suspension"]');
    await expect(this.page.locator('[role="status"]')).toContainText('User suspended');
  }
}
