import { apiFetch } from "./http";

export interface RuntimeStatus {
  runtime_version?: string;
  deployment?: string;
  air_gapped?: boolean;
  integrity?: Record<string, unknown>;
  store?: Record<string, unknown>;
  governance?: Record<string, unknown>;
}

export async function getSystemStatus(): Promise<RuntimeStatus> {
  return apiFetch<RuntimeStatus>("/api/v2/system/status");
}