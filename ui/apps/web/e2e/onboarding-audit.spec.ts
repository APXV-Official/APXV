import { expect, test } from "@playwright/test";
import { API_BASE, API_KEY } from "./constants";

async function repairAuditChain(request: import("@playwright/test").APIRequestContext) {
  try {
    await request.post(`${API_BASE}/api/v2/system/repair-audit`, {
      headers: { "APXV-API-KEY": API_KEY },
      timeout: 120_000,
    });
  } catch {
    // Large audit logs can exceed 2 minutes — tests continue without blocking.
  }
}

async function runDoctorUntilHealthy(page: import("@playwright/test").Page) {
  const openDashboard = page.getByRole("button", { name: "Open dashboard" });
  const continueAnyway = page.getByRole("button", { name: "Continue anyway" });
  const runDoctor = page.getByRole("button", { name: /^Run doctor$/i });

  if (await runDoctor.isVisible()) {
    await runDoctor.click();
    await expect(continueAnyway.or(openDashboard)).toBeVisible({ timeout: 30_000 });
  }

  if (await openDashboard.isVisible()) return;

  const repair = page.getByRole("button", { name: "Repair audit chain" });
  if (await repair.isVisible()) {
    await repair.click();
    await expect(
      page.getByText(/Audit chains repaired|review checks below/i).or(
        page.getByRole("button", { name: /Re-run doctor/i }),
      ),
    ).toBeVisible({ timeout: 30_000 });
    const reRunAfterRepair = page.getByRole("button", { name: /Re-run doctor/i });
    if (await reRunAfterRepair.isVisible()) {
      await reRunAfterRepair.click();
      await expect(continueAnyway.or(openDashboard)).toBeVisible({ timeout: 30_000 });
    }
  }

  if (await openDashboard.isVisible()) return;

  await expect(continueAnyway).toBeVisible({ timeout: 15_000 });
  await continueAnyway.click();
  await expect(openDashboard).toBeVisible({ timeout: 15_000 });
}

test.describe("onboarding audit", () => {
  test.beforeEach(async ({ page, request }) => {
    await repairAuditChain(request);
    await page.context().clearCookies();
    await page.addInitScript(() => {
      localStorage.clear();
    });
    await page.goto("/onboarding");
  });

  test("rejects bullet-only paste with clear error", async ({ page }) => {
    await page.getByRole("button", { name: "Continue" }).click();
    await page.locator("#api-key").fill("••••••••••••••••••••••••••••••••••••••••");
    await expect(
      page.getByText(/full operator key|43\+ characters/i),
    ).toBeVisible({ timeout: 10_000 });
    await expect(
      page.getByRole("button", { name: "Test connection" }),
    ).toBeDisabled();
    await page.screenshot({ path: "test-results/audit-onboarding-bullets.png" });
  });

  test("full connect flow with valid key reaches dashboard", async ({ page, request }) => {
    test.setTimeout(120_000);

    await page.getByRole("button", { name: "Continue" }).click();
    await page.locator("#api-key").fill(API_KEY);
    await page.getByRole("button", { name: "Test connection" }).click();
    await expect(
      page.getByText("Run a full system doctor check before entering the dashboard."),
    ).toBeVisible({ timeout: 15_000 });

    await repairAuditChain(request);
    await runDoctorUntilHealthy(page);
    await page.getByRole("button", { name: "Open dashboard" }).click();
    await expect(
      page.getByRole("heading", { level: 1, name: "Dashboard" }),
    ).toBeVisible({ timeout: 15_000 });
    await page.screenshot({ path: "test-results/audit-onboarding-success.png" });
  });

  test("extracts key when full OPERATOR-KEY file is pasted", async ({ page }) => {
    await page.getByRole("button", { name: "Continue" }).click();
    const fileSnippet = `APXV Operator API Key
Key ID: default-operator
API Key: ${API_KEY}`;
    await page.locator("#api-key").fill(fileSnippet);
    await page.getByRole("button", { name: "Test connection" }).click();
    await expect(
      page.getByText("Run a full system doctor check before entering the dashboard."),
    ).toBeVisible({ timeout: 15_000 });
  });
});