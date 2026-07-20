/**
 * E2E defaults. Set env vars against a live local instance:
 *   APXV_API_KEY, APXV_API_URL, APXV_UI_URL
 *
 * Never commit real operator keys. CI and local runs must supply APXV_API_KEY.
 */
export const API_KEY = process.env.APXV_API_KEY ?? "";

export const API_BASE = process.env.APXV_API_URL ?? "http://127.0.0.1:8741";
