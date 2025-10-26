import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  grep: /a11y/,
  use: {
    baseURL: 'http://localhost:3000/en',
    trace: 'off'
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    }
  ]
});
