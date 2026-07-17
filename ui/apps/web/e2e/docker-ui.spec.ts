import { expect, test } from "@playwright/test";
import { API_KEY } from "./constants";

/**
 * Row 13 — Docker nginx UI on :5173 with API proxied on same origin.
 * Run with APXV_SKIP_WEBSERVER=1 and APXV_UI_URL=http://127.0.0.1:5173
 */
test.describe("docker ui", () => {
  test.beforeEach(async ({ page }) => {
    test.skip(
      process.env.APXV_DOCKER_UI !== "1",
      "Set APXV_DOCKER_UI=1 to run Docker UI tests",
    );
    await page.context().clearCookies();
    await page.addInitScript(() => {
      localStorage.clear();
    });
  });

  test("first visit lands on setup with operator key", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/setup/, { timeout: 20_000 });
    await expect(page.getByRole("heading", { name: "Connect" })).toBeVisible();
    await expect(page.getByText("Discovered operator key")).toBeVisible();
    await expect(page.getByText(API_KEY)).toBeVisible({ timeout: 30_000 });
    await expect(page.getByLabel("Operator API key")).toBeVisible();
  });

  test("setup connect reaches dashboard", async ({ page }) => {
    test.setTimeout(120_000);

    await page.goto("/setup");
    await expect(page.getByText(API_KEY)).toBeVisible({ timeout: 30_000 });
    await page.getByRole("button", { name: "Connect" }).click();
    await expect(
      page.getByRole("heading", { level: 1, name: "Dashboard" }),
    ).toBeVisible({ timeout: 30_000 });
  });

  test("onboarded dashboard loads", async ({ page }) => {
    await page.context().addInitScript((apiKey: string) => {
      localStorage.setItem("apxv.apiKey", apiKey);
      localStorage.setItem("apxv.onboardingComplete", "true");
    }, API_KEY);
    await page.goto("/");
    await expect(
      page.getByRole("heading", { level: 1, name: "Dashboard" }),
    ).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("APXV™").first()).toBeVisible();
  });

  test("pipeline run from docker-served UI", async ({ page }) => {
    test.setTimeout(180_000);

    await page.context().addInitScript((apiKey: string) => {
      localStorage.setItem("apxv.apiKey", apiKey);
      localStorage.setItem("apxv.onboardingComplete", "true");
    }, API_KEY);
    await page.goto("/pipeline");
    await expect(
      page.getByRole("heading", { level: 1, name: "Pipeline" }),
    ).toBeVisible();
    await page.getByRole("button", { name: /Run pipeline/i }).click();
    await expect(page).toHaveURL(/\/jobs/, { timeout: 120_000 });
  });
});