import { test, expect } from "@playwright/test";
import { AxeBuilder } from "@axe-core/playwright";

const routes = ["/", "/search", "/listing/hh-seaside-loft"];

test.describe("accessibility", () => {
  for (const route of routes) {
    test(`has no obvious violations on ${route}`, async ({ page }) => {
      await page.goto(route);
      const results = await new AxeBuilder({ page }).analyze();
      expect(results.violations).toEqual([]);
    });
  }
});
