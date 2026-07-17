import { expect, test } from "@playwright/test";
import { API_KEY } from "./constants";

test.describe("desktop setup preview", () => {
  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await page.addInitScript((apiKey: string) => {
      localStorage.clear();
      (window as Window & { __APXV_TEST_OPERATOR_KEY__?: string }).__APXV_TEST_OPERATOR_KEY__ =
        apiKey;
    }, API_KEY);
    await page.goto("/setup-preview");
  });

  test("shows operator key and setup panels", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Connect" })).toBeVisible();
    await expect(page.getByText("Discovered operator key")).toBeVisible();
    await expect(page.getByText(API_KEY)).toBeVisible();
    await expect(page.getByLabel("Operator API key")).toHaveValue(API_KEY, {
      timeout: 15_000,
    });
    await expect(
      page.getByRole("button", { name: /^Connect/ }),
    ).toBeEnabled();
  });

  test("connect reaches dashboard", async ({ page }) => {
    test.setTimeout(90_000);

    await expect(page.getByLabel("Operator API key")).toHaveValue(API_KEY, {
      timeout: 15_000,
    });
    await page.getByRole("button", { name: /^Connect/ }).click();
    await expect(
      page.getByRole("heading", { level: 1, name: "Dashboard" }),
    ).toBeVisible({ timeout: 30_000 });
  });

  test("extracts key when full OPERATOR-KEY file is pasted", async ({ page }) => {
    await page.getByLabel("Operator API key").fill("");
    const fileSnippet = `APXV Operator API Key
Key ID: default-operator
API Key: ${API_KEY}`;
    await page.getByLabel("Operator API key").fill(fileSnippet);
    await expect(page.getByLabel("Operator API key")).toHaveValue(API_KEY);
    await page.getByRole("button", { name: /^Connect/ }).click();
    await expect(
      page.getByRole("heading", { level: 1, name: "Dashboard" }),
    ).toBeVisible({ timeout: 30_000 });
  });
});