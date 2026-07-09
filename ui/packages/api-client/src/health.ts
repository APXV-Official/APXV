import { apiFetch } from "./http";
import { getSystemStatus } from "./status";
import type { HealthResponse } from "./types";

/** Legacy v1 health — backward compatible. */
export async function getHealthLegacy(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

/** API v2 system health (preferred). */
export async function getSystemHealth(): Promise<
  HealthResponse & { api_version?: string }
> {
  return apiFetch("/api/v2/system/health");
}

/** Test authenticated connectivity (status + public health). */
export async function testApiConnection(): Promise<HealthResponse> {
  await getSystemStatus();
  return getSystemHealth();
}