import { defineConfig, devices } from "@playwright/test";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const port = Number(process.env.APXV_UI_PORT ?? "5174");
const baseURL = process.env.APXV_UI_URL ?? `http://127.0.0.1:${port}`;
const skipWebServer = process.env.APXV_SKIP_WEBSERVER === "1";
const storageState = join(
  fileURLToPath(new URL(".", import.meta.url)),
  "e2e",
  ".auth",
  "operator.json",
);

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 1,
  workers: 1,
  timeout: 45_000,
  reporter: "list",
  use: {
    baseURL,
    storageState,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  ...(skipWebServer
    ? {}
    : {
        webServer: {
          command: `pnpm exec vite --host 127.0.0.1 --port ${port} --strictPort`,
          url: baseURL,
          reuseExistingServer: Boolean(process.env.APXV_UI_URL),
          timeout: 120_000,
        },
      }),
});