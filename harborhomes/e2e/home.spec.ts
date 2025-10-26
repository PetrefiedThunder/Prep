import { test, expect } from "@playwright/test";

test("home search dialog flow", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /open search/i }).click();
  await expect(page.getByText(/Plan your next stay/)).toBeVisible();
});
