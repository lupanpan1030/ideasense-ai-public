import { defineConfig, devices } from "@playwright/test";

const port = Number(process.env.PLAYWRIGHT_PORT ?? "3002");
const baseURL =
  process.env.PLAYWRIGHT_BASE_URL ?? `http://localhost:${port}`;
const shouldStartWebServer = process.env.PLAYWRIGHT_SKIP_WEB_SERVER !== "1";

export default defineConfig({
  testDir: "./e2e",
  timeout: 45_000,
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI
    ? [["list"], ["html", { open: "never" }]]
    : [["list"]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  ...(shouldStartWebServer
    ? {
        webServer: {
          command: `npm run dev -- --hostname localhost --port ${port}`,
          url: baseURL,
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
          env: {
            BACKEND_INTERNAL_URL:
              process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000",
            NEXT_PUBLIC_API_BASE_URL:
              process.env.NEXT_PUBLIC_API_BASE_URL ??
              "http://localhost:8000/api/v1",
            NEXT_PUBLIC_ENABLE_DEV_LOGIN:
              process.env.NEXT_PUBLIC_ENABLE_DEV_LOGIN ?? "1",
          },
        },
      }
    : {}),
  projects: [
    {
      name: "chromium-desktop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: "chromium-mobile",
      use: {
        ...devices["Pixel 5"],
      },
    },
  ],
});
