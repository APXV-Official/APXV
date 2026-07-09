import { apiFetch } from "./http";

export async function getCapabilities(): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/v2/capabilities");
}