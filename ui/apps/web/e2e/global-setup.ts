import { request } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const API_BASE = process.env.APXV_API_URL ?? "http://127.0.0.1:8741";
const port = Number(process.env.APXV_UI_PORT ?? "5174");
const baseURL = process.env.APXV_UI_URL ?? `http://127.0.0.1:${port}`;
const apiKey =
  process.env.APXV_API_KEY ??
  "gnKiTGGjRimhIPWeoP9BLnumQVPClWxYVbAD8J_FXVM";

const __dirname = dirname(fileURLToPath(import.meta.url));
const storagePath = join(__dirname, ".auth", "operator.json");

export default async function globalSetup() {
  const ctx = await request.newContext();
  try {
    const health = await ctx.get(`${API_BASE}/api/v2/system/health`, {
      timeout: 5_000,
    });
    if (!health.ok()) {
      throw new Error(
        `APXV API not healthy at ${API_BASE}. Start: python -m scripts.apxv_serve`,
      );
    }
    const status = await ctx.get(`${API_BASE}/api/v2/system/status`, {
      headers: { "APXV-API-KEY": apiKey },
      timeout: 5_000,
    });
    if (!status.ok()) {
      throw new Error(
        `APXV-API-KEY auth failed (${status.status()}). Restart apxv_serve after auth changes.`,
      );
    }
    try {
      const repair = await ctx.post(`${API_BASE}/api/v2/system/repair-audit`, {
        headers: { "APXV-API-KEY": apiKey },
        timeout: 120_000,
      });
      if (!repair.ok()) {
        console.warn(
          `[global-setup] repair-audit returned ${repair.status()} — doctor may report chain_break`,
        );
      }
    } catch (err) {
      console.warn(
        `[global-setup] repair-audit skipped or timed out — continuing: ${(err as Error).message}`,
      );
    }
  } finally {
    await ctx.dispose();
  }

  mkdirSync(dirname(storagePath), { recursive: true });
  writeFileSync(
    storagePath,
    JSON.stringify(
      {
        cookies: [],
        origins: [
          {
            origin: baseURL,
            localStorage: [
              { name: "apxv.apiKey", value: apiKey },
              { name: "apxv.onboardingComplete", value: "true" },
            ],
          },
        ],
      },
      null,
      2,
    ),
  );
}