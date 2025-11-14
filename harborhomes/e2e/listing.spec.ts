import { test, expect } from "@playwright/test";

test("listing page shows gallery", async ({ page }) => {
  await page.goto("/listing/hh-seaside-loft");
  await expect(page.getByText(/About this stay/)).toBeVisible();
  await expect(page.getByText(/Amenities/)).toBeVisible();
});
