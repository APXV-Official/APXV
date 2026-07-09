import { expect, test } from "./fixtures";

const NAV_CASES = [
  { path: "/", title: "Dashboard" },
  { path: "/packs", title: "Agent packs" },
  { path: "/agents", title: "Agents" },
  { path: "/pipeline", title: "Pipeline" },
  { path: "/jobs", title: "Jobs" },
  { path: "/artifacts", title: "Artifacts" },
  { path: "/verify", title: "Verify" },
  { path: "/audit", title: "Audit" },
  { path: "/governance", title: "Governance" },
  { path: "/system", title: "System" },
  { path: "/settings", title: "Settings" },
] as const;

for (const { path, title } of NAV_CASES) {
  test(`loads ${path} — ${title}`, async ({ onboardedPage: page }) => {
    await page.goto(path);
    await expect(page).toHaveURL(new RegExp(`${path.replace("/", "\\/")}(\\?.*)?$`));
    await expect(
      page.getByRole("heading", { level: 1, name: title }),
    ).toBeVisible({ timeout: 20_000 });
  });
}

test("skip link focuses main content", async ({ onboardedPage: page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Skip to main content" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
});

test("pack studio — activate reference pack and run sample", async ({
  onboardedPage: page,
}) => {
  test.setTimeout(180_000);

  await page.goto("/packs");
  await expect(
    page.getByRole("heading", { level: 1, name: "Agent packs" }),
  ).toBeVisible();

  await page
    .getByRole("button", { name: /Reference Redaction/i })
    .first()
    .click();

  const setActive = page.getByRole("button", { name: "Set active" });
  if ((await setActive.count()) > 0) {
    await setActive.click();
  }

  await expect(
    page.getByRole("alert").filter({ hasText: "Active pack" }),
  ).toBeVisible({ timeout: 20_000 });

  await page.getByRole("button", { name: "Run pack (sample input)" }).click();
  await expect(page).toHaveURL(/\/jobs/, { timeout: 120_000 });
});

test("agent registry lists core agents", async ({ onboardedPage: page }) => {
  await page.goto("/agents");
  await expect(page.getByRole("heading", { level: 1, name: "Agents" })).toBeVisible();
  await expect(
    page.getByRole("button", { name: /RuleGovernedRedactor/i }),
  ).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("APXV-AGENT-001").first()).toBeVisible();
});

test("pipeline shows agent chain preview", async ({ onboardedPage: page }) => {
  await page.goto("/pipeline");
  await expect(page.getByRole("heading", { level: 1, name: "Pipeline" })).toBeVisible();
  await expect(page.getByText("Agent chain")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("APXV-AGENT-001")).toBeVisible();
});

test("jobs detail deep link", async ({ onboardedPage: page, request }) => {
  test.setTimeout(45_000);

  const apiBase = process.env.APXV_API_URL ?? "http://127.0.0.1:8741";
  const apiKey =
    process.env.APXV_API_KEY ??
    "gnKiTGGjRimhIPWeoP9BLnumQVPClWxYVbAD8J_FXVM";

  const jobsRes = await request.get(`${apiBase}/api/v2/jobs?limit=1`, {
    headers: { "APXV-API-KEY": apiKey },
  });
  expect(jobsRes.ok()).toBeTruthy();
  const jobsBody = (await jobsRes.json()) as { items?: { id: string }[] };
  const jobId = jobsBody.items?.[0]?.id;
  test.skip(!jobId, "No jobs in runtime — run a pipeline first");

  await page.goto(`/jobs?id=${encodeURIComponent(jobId!)}`);
  await expect(page.getByRole("heading", { level: 1, name: "Jobs" })).toBeVisible();
  await expect(page.getByText("Job detail")).toBeVisible({ timeout: 15_000 });
  await expect(page.locator(`[title="${jobId}"]`)).toBeVisible();
});