import { test, expect } from '@playwright/test';

test('listing detail interactions', async ({ page }) => {
  await page.goto('/listing/harbor-loft');
  await expect(page.getByRole('heading', { name: /Sunrise Loft/ })).toBeVisible();
  await expect(page.getByText(/Amenities/)).toBeVisible();
  await page.getByRole('button', { name: /Continue/i }).click();
  await expect(page).toHaveURL(/checkout/);
});
