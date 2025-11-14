import { Page, expect } from '@playwright/test';
import { KitchenPayload } from '../utils/testDataApi';

export class HostDashboardPage {
  constructor(private readonly page: Page) {}

  async gotoDashboard() {
    await this.page.goto('/host/dashboard');
    await expect(this.page.locator('[data-testid="host-dashboard"]')).toBeVisible();
  }

  async startNewListing() {
    await this.page.click('[data-testid="create-listing"]');
    await expect(this.page.locator('[data-testid="listing-form"]')).toBeVisible();
  }

  async fillListingForm(kitchen: KitchenPayload) {
    await this.page.fill('[data-testid="listing-name"]', kitchen.name);
    await this.page.fill('[data-testid="listing-address"]', kitchen.address);
    await this.page.fill('[data-testid="listing-capacity"]', kitchen.capacity.toString());
    await this.page.fill('[data-testid="listing-hourly-rate"]', kitchen.hourlyRate.toString());

    for (const equipment of kitchen.equipment) {
      await this.page.fill('[data-testid="listing-equipment-input"]', equipment);
      await this.page.keyboard.press('Enter');
    }

    for (const amenity of kitchen.amenities) {
      await this.page.fill('[data-testid="listing-amenities-input"]', amenity);
      await this.page.keyboard.press('Enter');
    }

    await this.page.fill('[data-testid="listing-availability-start"]', kitchen.availability.start);
    await this.page.fill('[data-testid="listing-availability-end"]', kitchen.availability.end);
  }

  async submitListing() {
    await this.page.click('[data-testid="submit-listing"]');
    await expect(this.page.locator('[role="status"]')).toContainText('Listing submitted for review');
  }

  async uploadCertification(documentPath: string) {
    const fileChooserPromise = this.page.waitForEvent('filechooser');
    await this.page.click('[data-testid="upload-certification"]');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles(documentPath);
    await expect(this.page.locator('[role="status"]')).toContainText('Certification uploaded');
  }

  async openAnalytics() {
    await this.page.click('[data-testid="analytics-tab"]');
    await expect(this.page.locator('[data-testid="analytics-dashboard"]')).toBeVisible();
  }
}
