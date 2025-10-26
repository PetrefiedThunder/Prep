import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('a11y home', async ({ page }) => {
  await page.goto('/');
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test('a11y search', async ({ page }) => {
  await page.goto('/search');
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test('a11y listing', async ({ page }) => {
  await page.goto('/listing/harbor-loft');
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
