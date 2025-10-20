import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './specs',
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    headless: true,
  },
});
