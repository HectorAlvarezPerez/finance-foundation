import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  outputDir: "./.playwright/test-results",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  timeout: 60000,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ["list"],
    ["html", { outputFolder: "./.playwright/report", open: "never" }],
  ],
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "bash -lc 'cd ../.. && npm run e2e:backend'",
      url: "http://localhost:8000/api/v1/health",
      reuseExistingServer: true,
      timeout: 30000,
    },
    {
      command:
        "bash -lc 'unset npm_config_prefix && source ~/.nvm/nvm.sh || true && nvm use 20 || true && cd ../.. && NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm --workspace apps/frontend run dev'",
      url: "http://localhost:3000/login",
      reuseExistingServer: true,
      timeout: 60000,
    },
  ],
});
