import { expect, test } from "./fixtures";
import { API_BASE, API_KEY } from "./constants";

const SIDEBAR_NAV = [
  { label: "Dashboard", path: "/", heading: "Dashboard" },
  { label: "Agent packs", path: "/packs", heading: "Agent packs" },
  { label: "Agents", path: "/agents", heading: "Agents" },
  { label: "Pipeline", path: "/pipeline", heading: "Pipeline" },
  { label: "Jobs", path: "/jobs", heading: "Jobs" },
  { label: "Artifacts", path: "/artifacts", heading: "Artifacts" },
  { label: "Verify", path: "/verify", heading: "Verify" },
  { label: "Audit", path: "/audit", heading: "Audit" },
  { label: "Governance", path: "/governance", heading: "Governance" },
  { label: "System", path: "/system", heading: "System" },
  { label: "Settings", path: "/settings", heading: "Settings" },
] as const;

test.describe("full app smoke", () => {
  test("sidebar navigates every primary route", async ({ onboardedPage: page }) => {
    await page.goto("/");
    for (const { label, path, heading } of SIDEBAR_NAV) {
      await page.getByRole("navigation", { name: "Application" }).getByRole("link", { name: label }).click();
      await expect(page).toHaveURL(new RegExp(`${path.replace("/", "\\/")}(\\?.*)?$`));
      await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible({
        timeout: 20_000,
      });
    }
  });

  test("global refresh button works on dashboard", async ({ onboardedPage: page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Refresh all data from the runtime" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Dashboard" })).toBeVisible();
  });

  test("command palette opens", async ({ onboardedPage: page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Open command palette" }).click();
    await expect(page.getByPlaceholder("Search pages and actions…")).toBeVisible({
      timeout: 10_000,
    });
  });

  test("dashboard quick run reaches jobs", async ({ onboardedPage: page }) => {
    test.setTimeout(180_000);
    await page.goto("/");
    await page.getByRole("button", { name: "Run reference pipeline" }).click();
    await expect(page).toHaveURL(/\/jobs/, { timeout: 120_000 });
    await expect(page.getByText("Job detail")).toBeVisible({ timeout: 30_000 });
  });

  test("packs — select each official pack", async ({ onboardedPage: page }) => {
    await page.goto("/packs");
    const packs = [
      /Reference Redaction/i,
      /Document Processing/i,
      /AI Governance/i,
    ];
    for (const name of packs) {
      await page.getByRole("button", { name }).first().click();
      await expect(page.getByRole("heading", { level: 2, name })).toBeVisible({
        timeout: 15_000,
      });
    }
  });

  test("agents — select core redactor", async ({ onboardedPage: page }) => {
    await page.goto("/agents");
    await page.getByRole("button", { name: /RuleGovernedRedactor/i }).click();
    await expect(
      page.getByRole("heading", { level: 2, name: /RuleGovernedRedactor/i }),
    ).toBeVisible();
  });

  test("pipeline — reference run with attestation", async ({ onboardedPage: page }) => {
    test.setTimeout(180_000);
    await page.goto("/pipeline");
    const attest = page.locator("#attest");
    if (!(await attest.isChecked())) {
      await attest.check();
    }
    await page.getByRole("button", { name: "Run pipeline" }).click();
    await expect(page).toHaveURL(/\/jobs/, { timeout: 120_000 });
    await expect(page.getByRole("heading", { name: "Job detail" })).toBeVisible({
      timeout: 60_000,
    });
  });

  test("pipeline — AI governance pack completes", async ({ onboardedPage: page }) => {
    test.setTimeout(180_000);
    await page.goto("/pipeline");
    await page.locator("#pack").selectOption("apxv-pack-ai-governance");
    await page.locator("#input-text").fill(
      "Contact: jane@example.com, phone (555) 123-4567, SSN 123-45-6789.",
    );
    await page.getByRole("button", { name: "Run pipeline" }).click();
    await expect(page).toHaveURL(/\/jobs/, { timeout: 120_000 });
    await expect(page.getByRole("heading", { name: "Job detail" })).toBeVisible({
      timeout: 90_000,
    });
    const failed = page.locator("main").getByText(/^failed$/i);
    if (await failed.isVisible()) {
      const detail = await page.locator("pre, code, .font-mono").first().textContent();
      throw new Error(`AI governance job failed: ${detail?.slice(0, 500)}`);
    }
  });

  test("jobs — refresh list", async ({ onboardedPage: page }) => {
    await page.goto("/jobs");
    await page.getByRole("button", { name: "Refresh" }).first().click();
    await expect(page.getByRole("heading", { name: "Job queue" })).toBeVisible();
  });

  test("artifacts — library loads", async ({ onboardedPage: page }) => {
    await page.goto("/artifacts");
    await expect(page.getByRole("heading", { name: "Artifact library" })).toBeVisible();
    await page
      .getByRole("main")
      .getByRole("button", { name: "Refresh", exact: true })
      .click();
  });

  test("artifacts — open detail when available", async ({
    onboardedPage: page,
    request,
  }) => {
    const res = await request.get(`${API_BASE}/api/v2/artifacts?limit=20`, {
      headers: { "APXV-API-KEY": API_KEY },
    });
    expect(res.ok()).toBeTruthy();
    const body = (await res.json()) as {
      items?: { artifact_hash: string; name: string }[];
    };
    const hash =
      body.items?.find((a) => a.name.toLowerCase().includes("attest"))
        ?.artifact_hash ?? body.items?.[0]?.artifact_hash;
    test.skip(!hash, "No artifacts yet");

    await page.goto("/artifacts");
    await expect(
      page.getByRole("heading", { name: "Artifact library" }),
    ).toBeVisible({ timeout: 20_000 });
    const artifactLink = page.locator(`a[href="/artifacts/${hash}"]`);
    if ((await artifactLink.count()) > 0) {
      await artifactLink.first().click();
    } else {
      await page.getByRole("link", { name: "Open" }).first().click();
    }
    await expect(page).toHaveURL(new RegExp(`/artifacts/${hash.slice(0, 8)}`), {
      timeout: 20_000,
    });
    await expect(page.getByRole("tab", { name: "Summary" })).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByRole("tab", { name: "Verify" })).toBeVisible();
  });

  test("verify — page controls present", async ({ onboardedPage: page }) => {
    await page.goto("/verify");
    await expect(page.getByRole("heading", { name: "Attestation verifier" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Verify attestation/i })).toBeVisible();
    await expect(page.getByLabel(/artifact hash/i)).toBeVisible();
  });

  test("audit — log list and refresh", async ({ onboardedPage: page }) => {
    await page.goto("/audit");
    await expect(page.getByRole("heading", { name: "Audit logs" })).toBeVisible();
    const firstLog = page.getByRole("button", { name: /audit\.log/i }).first();
    if ((await firstLog.count()) > 0) {
      await firstLog.click();
      await expect(page.getByRole("heading", { name: "Audit explorer" })).toBeVisible({
        timeout: 15_000,
      });
    }
    await page.getByRole("button", { name: "Refresh" }).last().click();
  });

  test("governance — specs and proposals tabs", async ({ onboardedPage: page }) => {
    await page.goto("/governance");
    await expect(page.getByRole("heading", { level: 1, name: "Governance" })).toBeVisible();
    await page.getByRole("tab", { name: "Governance studio" }).click();
    await expect(page.getByRole("button", { name: "rule" })).toBeVisible({
      timeout: 15_000,
    });
    await page.getByRole("tab", { name: /Proposals/i }).click();
    await expect(page.getByRole("heading", { name: "Proposal queue" })).toBeVisible({
      timeout: 15_000,
    });
  });

  test("system — all tabs load", async ({ onboardedPage: page }) => {
    await page.goto("/system");
    await page.getByRole("tab", { name: "System health" }).click();
    await expect(page.getByRole("heading", { name: "Doctor checks" })).toBeVisible({
      timeout: 20_000,
    });
    await page.getByRole("tab", { name: "Backups" }).click();
    await expect(page.getByRole("heading", { name: "Backup archives" })).toBeVisible({
      timeout: 15_000,
    });
    await page.getByRole("tab", { name: "Integrations" }).click();
    await expect(page.getByText(/Ollama/i).first()).toBeVisible({ timeout: 15_000 });
  });

  test("settings — connection and API keys sections", async ({ onboardedPage: page }) => {
    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: "Connection" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "API keys" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Verifier bundle" })).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Download verifier bundle/i }),
    ).toBeVisible();
  });
});