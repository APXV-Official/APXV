import { test as base } from "@playwright/test";
import { API_KEY as DEFAULT_API_KEY } from "./constants";

export const test = base.extend({
  onboardedPage: async ({ page }, use) => {
    if (!DEFAULT_API_KEY) {
      throw new Error(
        "Set APXV_API_KEY to a valid operator key before running e2e tests.",
      );
    }
    await page.context().addInitScript((apiKey: string) => {
      localStorage.setItem("apxv.apiKey", apiKey);
      localStorage.setItem("apxv.onboardingComplete", "true");
    }, DEFAULT_API_KEY);
    await page.goto("/");
    // Endgame home is Workbench (/workshop); chrome may say Workshop or show shelf
    await page
      .getByRole("navigation", { name: "Application" })
      .getByRole("link", { name: "Workbench" })
      .waitFor({ timeout: 25_000 });
    await use(page);
  },
});

export { expect } from "@playwright/test";