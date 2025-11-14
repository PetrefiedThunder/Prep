import { test, expect } from '@playwright/test';

test('home to search flow', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Stay with ease/ })).toBeVisible();
  await page.getByRole('link', { name: /Start exploring/ }).click();
  await expect(page).toHaveURL(/search/);
});
