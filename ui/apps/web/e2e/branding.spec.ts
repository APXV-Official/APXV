import { expect, test } from "./fixtures";

/** Bare "APX" / "APXV1" — not substrings of APXV. */
const LEGACY_BRAND = /\b(?:APX(?!V)|APXV1)\b/;

async function expectNoLegacyBrand(page: import("@playwright/test").Page) {
  const body = await page.locator("body").innerText();
  expect(body).not.toMatch(LEGACY_BRAND);
}

const SHELL_PAGES = [
  "/",
  "/packs",
  "/agents",
  "/pipeline",
  "/jobs",
  "/artifacts",
  "/verify",
  "/audit",
  "/governance",
  "/governance?tab=specs",
  "/system",
  "/settings",
] as const;

test("sidebar shows APXV platform branding (not APXV1)", async ({
  onboardedPage: page,
}) => {
  await page.goto("/");

  const nav = page.getByRole("complementary", { name: "Primary navigation" });
  await expect(nav.getByText("APXV™", { exact: true })).toBeVisible();
  await expect(
    nav.getByText("Sovereign operator console", { exact: true }),
  ).toBeVisible();
  await expect(nav.getByText("APXV1", { exact: true })).toHaveCount(0);

  await page.screenshot({
    path: "test-results/branding-sidebar.png",
    fullPage: false,
  });
});

test("onboarding shows APXV logo without legacy APXV1 suffix", async ({
  page,
}) => {
  await page.context().clearCookies();
  await page.addInitScript(() => {
    localStorage.removeItem("apxv.apiKey");
    localStorage.removeItem("apxv.onboardingComplete");
  });
  await page.goto("/onboarding");

  await expect(page.getByText("APXV™", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("APXV1", { exact: true })).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Operator setup" }),
  ).toBeVisible();

  await page.screenshot({
    path: "test-results/branding-onboarding.png",
    fullPage: true,
  });
});

test("shell pages use APXV branding only (no bare APX or APXV1)", async ({
  onboardedPage: page,
}) => {
  for (const path of SHELL_PAGES) {
    await page.goto(path);
    await page.waitForLoadState("domcontentloaded");
    await page.getByRole("main").waitFor({ timeout: 15_000 });
    await expectNoLegacyBrand(page);
  }
});

test("governance spec preview shows APXV not APX", async ({
  onboardedPage: page,
}) => {
  await page.goto("/governance?tab=specs");
  await page.getByRole("main").waitFor({ timeout: 15_000 });

  const purpose = page.getByText(/minimum redaction behavior/i);
  if ((await purpose.count()) > 0) {
    await expect(purpose.first()).toContainText("APXV agent");
    await expect(purpose.first()).not.toContainText("APX agent");
  }

  await expectNoLegacyBrand(page);
});