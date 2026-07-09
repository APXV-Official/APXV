import { expect, test } from "@playwright/test";

const API_KEY =
  process.env.APXV_API_KEY ??
  "gnKiTGGjRimhIPWeoP9BLnumQVPClWxYVbAD8J_FXVM";

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
    await expect(page.getByRole("heading", { name: "Setup" })).toBeVisible();
    await expect(page.getByText("Your operator key")).toBeVisible();
    await expect(page.getByText(API_KEY)).toBeVisible();
    await expect(page.getByLabel("Paste operator key")).toBeVisible();
    await expect(page.getByRole("button", { name: "Connect" })).toBeVisible();
  });

  test("connect reaches dashboard", async ({ page }) => {
    test.setTimeout(90_000);

    await page.getByLabel("Paste operator key").fill(API_KEY);
    await page.getByRole("button", { name: "Connect" }).click();
    await expect(
      page.getByRole("heading", { level: 1, name: "Dashboard" }),
    ).toBeVisible({ timeout: 30_000 });
  });

  test("extracts key when full OPERATOR-KEY file is pasted", async ({ page }) => {
    const fileSnippet = `APXV Operator API Key
Key ID: default-operator
API Key: ${API_KEY}`;
    await page.getByLabel("Paste operator key").fill(fileSnippet);
    await page.getByRole("button", { name: "Connect" }).click();
    await expect(
      page.getByRole("heading", { level: 1, name: "Dashboard" }),
    ).toBeVisible({ timeout: 30_000 });
  });
});