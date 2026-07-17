import { expect, test } from "./fixtures";

test("dashboard — Build your pipeline opens pack wizard", async ({
  onboardedPage: page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { level: 1, name: "Dashboard" }),
  ).toBeVisible();

  await page.getByRole("link", { name: "Start pack wizard" }).click();
  await expect(page).toHaveURL(/\/packs\?wizard=1|\/packs\?wizard=%221%22/);
  const wizard = page.getByRole("region", { name: "Pack authoring wizard" });
  await expect(wizard).toBeVisible({ timeout: 15_000 });
  await expect(
    page.getByRole("heading", { name: "Pack authoring wizard" }),
  ).toBeVisible();
});

test("pack studio — wizard deep link shows five steps", async ({
  onboardedPage: page,
}) => {
  await page.goto("/packs?wizard=1");
  await expect(
    page.getByRole("heading", { level: 1, name: "Agent packs" }),
  ).toBeVisible({ timeout: 20_000 });

  const wizard = page.getByRole("region", { name: "Pack authoring wizard" });
  await expect(wizard).toBeVisible({ timeout: 15_000 });
  const progress = wizard.getByRole("navigation", { name: "Wizard progress" });
  for (const step of ["Template", "Name pack", "Governance", "Activate", "Test run"]) {
    await expect(progress).toContainText(step);
  }
});