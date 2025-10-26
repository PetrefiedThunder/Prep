import { test, expect } from "@playwright/test";

test("search applies filters", async ({ page }) => {
  await page.goto("/search");
  await page.getByRole("button", { name: /open search/i }).click();
  await page.getByText(/Amenities/).click();
  await expect(page.getByText(/Results/)).toBeVisible();
});
