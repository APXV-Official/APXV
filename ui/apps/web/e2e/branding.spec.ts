import { expect, test } from "./fixtures";

test("sidebar shows APXV platform branding (not APXV1)", async ({
  onboardedPage: page,
}) => {
  await page.goto("/");

  const nav = page.getByRole("complementary", { name: "Primary navigation" });
  await expect(nav.getByText("APXV", { exact: true })).toBeVisible();
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

  await expect(page.getByText("APXV", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("APXV1", { exact: true })).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Operator setup" }),
  ).toBeVisible();

  await page.screenshot({
    path: "test-results/branding-onboarding.png",
    fullPage: true,
  });
});