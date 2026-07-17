import { test as base } from "@playwright/test";
import { API_KEY as DEFAULT_API_KEY } from "./constants";

export const test = base.extend({
  onboardedPage: async ({ page }, use) => {
    await page.context().addInitScript((apiKey: string) => {
      localStorage.setItem("apxv.apiKey", apiKey);
      localStorage.setItem("apxv.onboardingComplete", "true");
    }, DEFAULT_API_KEY);
    await page.goto("/");
    await page
      .getByRole("heading", { level: 1, name: "Dashboard" })
      .waitFor({ timeout: 20_000 });
    await use(page);
  },
});

export { expect } from "@playwright/test";