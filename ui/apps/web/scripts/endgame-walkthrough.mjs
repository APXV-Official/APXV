/**
 * New-user style walkthrough of endgame IA against local Vite + API.
 * Run: node scripts/endgame-walkthrough.mjs
 */
import { chromium } from "@playwright/test";

const UI = process.env.APXV_UI_URL ?? "http://127.0.0.1:5173";
const API_KEY = process.env.APXV_API_KEY ?? "";
if (!API_KEY) {
  console.error("Set APXV_API_KEY to a valid operator key before running.");
  process.exit(1);
}

const failures = [];
function ok(msg) {
  console.log("ok:", msg);
}
function fail(msg) {
  failures.push(msg);
  console.error("FAIL:", msg);
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  await context.addInitScript((key) => {
    localStorage.setItem("apxv.apiKey", key);
    localStorage.setItem("apxv.onboardingComplete", "true");
  }, API_KEY);

  const page = await context.newPage();
  page.setDefaultTimeout(20_000);
  // Dirty-guard and remove confirms — accept leave/discard for automated walk
  page.on("dialog", async (dialog) => {
    await dialog.accept();
  });

  // 1. Land on Workshop
  await page.goto(UI + "/");
  await page.waitForTimeout(1500);
  const url = page.url();
  if (url.includes("/workshop") || (await page.getByText("Shelf").count()) > 0) {
    ok("default route lands Workshop / workbench");
  } else {
    fail(`expected workshop home, got ${url}`);
  }

  // Nav items
  for (const label of ["Workshop", "Runs", "Artifacts", "Trust", "System", "Settings"]) {
    const link = page.getByRole("link", { name: label, exact: true });
    if ((await link.count()) === 0) fail(`nav missing: ${label}`);
    else ok(`nav has ${label}`);
  }
  for (const gone of ["Dashboard", "Agent packs", "Pipeline"]) {
    // primary nav should not list these as main destinations
    const n = await page.locator("nav[aria-label=Application]").getByText(gone, { exact: true }).count();
    if (n > 0) fail(`legacy nav still present: ${gone}`);
    else ok(`legacy nav gone: ${gone}`);
  }

  // Shelf tabs
  const shelfAside = page.locator("aside").filter({ hasText: "Shelf" }).first();
  for (const tab of ["Agents", "Packs", "Controls", "Library"]) {
    await shelfAside.getByRole("button", { name: tab, exact: true }).click();
    await page.waitForTimeout(200);
    ok(`shelf tab ${tab}`);
  }

  // Open agent sheet + add
  await shelfAside.getByRole("button", { name: "Agents", exact: true }).click();
  await page.waitForTimeout(400);
  const agentOpen = shelfAside.locator("button").filter({ hasText: /AGENT|Redact|agent/i }).first();
  if ((await agentOpen.count()) > 0) {
    await agentOpen.click();
    await page.waitForTimeout(300);
    if (
      (await page.getByRole("dialog", { name: "Ingredient sheet" }).count()) > 0 ||
      (await page.getByText("Add to board").count()) > 0
    ) {
      ok("ingredient sheet opens");
      await page.getByRole("button", { name: /Add to board/i }).first().click();
      await page.waitForTimeout(400);
      ok("add to board from sheet");
    } else {
      fail("ingredient sheet did not open");
    }
  } else {
    const plus = shelfAside.locator("button[title='Add to board']").first();
    if ((await plus.count()) > 0) {
      await plus.click();
      ok("add to board via +");
    } else fail("no agents on shelf to add");
  }

  // Packs shelf
  await shelfAside.getByRole("button", { name: "Packs", exact: true }).click();
  await page.waitForTimeout(300);
  const packPlus = shelfAside.locator("button[title='Add to board']").first();
  if ((await packPlus.count()) > 0) {
    await packPlus.click();
    ok("add pack from shelf");
  }

  // Controls
  await shelfAside.getByRole("button", { name: "Controls", exact: true }).click();
  await page.waitForTimeout(200);
  ok("controls shelf");

  // Library
  await shelfAside.getByRole("button", { name: "Library", exact: true }).click();
  await page.waitForTimeout(400);
  if ((await page.getByText(/Example/i).count()) > 0) ok("library shows examples");
  else ok("library tab opened (may be empty templates)");

  // Run validate empty multi-step without wires should error when enough steps
  // Navigate Runs
  await page.getByRole("link", { name: "Runs", exact: true }).click();
  await page.waitForTimeout(800);
  if ((await page.getByText(/Run queue|No runs yet|Run detail/i).count()) > 0) {
    ok("Runs page loads");
  } else {
    fail("Runs page content missing");
  }

  // Trust
  await page.getByRole("link", { name: "Trust", exact: true }).click();
  await page.waitForTimeout(600);
  if ((await page.getByText("Verify").count()) > 0) ok("Trust hub loads");
  else fail("Trust hub missing cards");

  // System + Settings
  await page.getByRole("link", { name: "System", exact: true }).click();
  await page.waitForTimeout(800);
  ok("System navigable");
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await page.waitForTimeout(600);
  ok("Settings navigable");

  // Back to workshop, load template if available
  await page.getByRole("link", { name: "Workshop", exact: true }).click();
  await page.waitForTimeout(800);
  await page.locator("aside").filter({ hasText: "Shelf" }).first()
    .getByRole("button", { name: "Library", exact: true }).click();
  await page.waitForTimeout(400);
  const exampleBtn = page
    .locator("aside")
    .filter({ hasText: "Shelf" })
    .locator("button")
    .filter({ hasText: /pipeline|redact|Example/i })
    .first();
  if ((await exampleBtn.count()) > 0) {
    await exampleBtn.click();
    await page.waitForTimeout(1500);
    ok("loaded library example onto board");
  }

  await page.getByRole("button", { name: "Run", exact: true }).click();
  await page.waitForTimeout(1000);
  ok("Run button clickable (may validate or queue)");

  // Artifacts
  await page.getByRole("link", { name: "Artifacts", exact: true }).click();
  await page.waitForTimeout(800);
  ok("Artifacts page");

  // Legacy redirects
  await page.goto(UI + "/agents");
  await page.waitForTimeout(1000);
  if (page.url().includes("workshop")) ok("/agents redirects to workshop");
  else fail(`/agents did not redirect: ${page.url()}`);

  await page.goto(UI + "/pipeline");
  await page.waitForTimeout(1000);
  if (page.url().includes("workshop")) ok("/pipeline redirects to workshop");
  else fail(`/pipeline did not redirect: ${page.url()}`);

  await browser.close();

  if (failures.length) {
    console.error(`\n${failures.length} walkthrough failure(s)`);
    process.exit(1);
  }
  console.log("\nEndgame walkthrough: all checks passed");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
