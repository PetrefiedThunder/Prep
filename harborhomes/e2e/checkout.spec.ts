import { test, expect } from "@playwright/test";

test("checkout flow", async ({ page }) => {
  await page.goto("/checkout/hh-seaside-loft");
  await expect(page.getByText(/Review your stay/)).toBeVisible();
});
