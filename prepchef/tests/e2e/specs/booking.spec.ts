import { test, expect } from '@playwright/test';

test('user can create a booking', async ({ page }) => {
  await page.goto('/bookings');
  await page.click('text="New Booking"');
  await page.fill('input[name="date"]', '2025-01-01');
  await page.click('button[type="submit"]');
  await expect(page.locator('text=Booking confirmed')).toBeVisible();
});
