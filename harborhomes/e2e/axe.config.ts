import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./",
  testMatch: "axe.spec.ts",
  reporter: "list"
});
