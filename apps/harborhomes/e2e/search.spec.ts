import { test, expect } from '@playwright/test';

test('apply filters on search', async ({ page }) => {
  await page.goto('/search');
  await page.getByRole('button', { name: /Open filters/i }).click();
  await page.getByRole('button', { name: /wifi/i }).click();
  await page.getByRole('button', { name: /apply filters/i }).click();
  await expect(page.getByText(/curated homes/i)).toBeVisible();
});
