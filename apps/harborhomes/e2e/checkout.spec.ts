import { test, expect } from '@playwright/test';

test('complete checkout flow', async ({ page }) => {
  await page.goto('/checkout/harbor-loft');
  await page.getByRole('button', { name: /Continue to details/ }).click();
  await page.getByLabel(/Full name/).fill('Jordan Harbor');
  await page.getByLabel(/Email/).fill('guest@example.com');
  await page.getByLabel(/Phone/).fill('5550000000');
  await page.getByRole('button', { name: /Save details/ }).click();
  await page.getByRole('button', { name: /Complete booking/ }).click();
  await expect(page.getByText(/All set/)).toBeVisible();
});
