import { expect, test } from "@playwright/test";

const API_BASE = process.env.APXV_API_URL ?? "http://127.0.0.1:8741";
const API_KEY =
  process.env.APXV_API_KEY ??
  "gnKiTGGjRimhIPWeoP9BLnumQVPClWxYVbAD8J_FXVM";

test("APXV-API-KEY authenticates v2 status endpoint", async ({ request }) => {
  const response = await request.get(`${API_BASE}/api/v2/system/status`, {
    headers: { "APXV-API-KEY": API_KEY },
  });
  expect(response.status()).toBe(200);
  const body = await response.json();
  expect(body.runtime_version).toBeTruthy();
});

test("health endpoint does not require auth", async ({ request }) => {
  const response = await request.get(`${API_BASE}/api/v2/system/health`);
  expect(response.status()).toBe(200);
});