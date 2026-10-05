import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: '**/*.browser.spec.ts',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  outputDir: 'test-results',
  reporter: [['list']],
  use: {
    channel: 'chrome',
    headless: true,
    baseURL: 'http://127.0.0.1:8510',
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 1,
    screenshot: 'only-on-failure',
    trace: 'off',
  },
});
