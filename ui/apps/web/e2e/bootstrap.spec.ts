import { expect, test } from "@playwright/test";

test.describe("desktop bootstrap preview", () => {
  test.beforeEach(async ({ page }) => {
    await page.context().clearCookies();
    await page.addInitScript(() => {
      localStorage.clear();
    });
    await page.goto("/bootstrap-preview");
  });

  test("shows sovereign bootstrap wizard", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Bootstrap" })).toBeVisible();
    await expect(
      page.getByText("Sovereign setup — your machine generates your proving keys"),
    ).toBeVisible();
    await expect(page.getByText("ZK trusted setup")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Start sovereign bootstrap" }),
    ).toBeVisible();
  });

  test("start shows progress lines in preview mode", async ({ page }) => {
    await page.getByRole("button", { name: "Start sovereign bootstrap" }).click();
    await expect(page.getByText("[1/9] Preflight")).toBeVisible();
    await expect(page.getByText("Bootstrap running…")).toBeVisible();
  });

  test("optional integration skip toggles", async ({ page }) => {
    await page.getByLabel("Skip Ollama").click();
    await page.getByLabel("Skip Vosk voice model download").click();
    await expect(page.getByLabel("Skip Ollama")).toBeChecked();
    await expect(page.getByLabel("Skip Vosk voice model download")).toBeChecked();
  });
});