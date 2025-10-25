import { Page, expect } from '@playwright/test';

export class RenterExperiencePage {
  constructor(private readonly page: Page) {}

  async searchForKitchen(query: string) {
    await this.page.goto('/kitchens');
    await expect(this.page.locator('[data-testid="kitchen-search"]')).toBeVisible();
    await this.page.fill('[data-testid="kitchen-search"]', query);
    await this.page.click('[data-testid="kitchen-search-submit"]');
    await expect(this.page.locator('[data-testid="search-results"]')).toContainText(query);
  }

  async openKitchenDetails(slug: string) {
    await this.page.click(`[data-testid="kitchen-card-${slug}"]`);
    await expect(this.page.locator('[data-testid="kitchen-detail"]')).toBeVisible();
  }

  async bookTimeslot({ start, end }: { start: string; end: string }) {
    await this.page.fill('[data-testid="booking-start"]', start);
    await this.page.fill('[data-testid="booking-end"]', end);
    await this.page.click('[data-testid="submit-booking"]');
    await expect(this.page.locator('[role="status"]')).toContainText('Booking confirmed');
  }

  async submitReview({ rating, review }: { rating: number; review: string }) {
    await this.page.click('[data-testid="open-review-form"]');
    await expect(this.page.locator('[data-testid="review-form"]')).toBeVisible();
    await this.page.click(`[data-testid="rating-star-${rating}"]`);
    await this.page.fill('[data-testid="review-comment"]', review);
    await this.page.click('[data-testid="submit-review"]');
    await expect(this.page.locator('[role="status"]')).toContainText('Review submitted');
  }
}
