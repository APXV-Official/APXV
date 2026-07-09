import { apiFetch } from "./http";
import type { OllamaStatus } from "./integrations";

export interface IntegrationRepairResult {
  ok: boolean;
  install_json_updated: boolean;
  ollama: {
    enabled?: boolean;
    verified?: boolean;
    model?: string | null;
    detail?: string;
    api?: OllamaStatus;
  };
  voice: {
    enabled?: boolean;
    backend?: string | null;
    model?: string | null;
    detail?: string;
  };
}

export async function repairIntegrations(): Promise<IntegrationRepairResult> {
  return apiFetch<IntegrationRepairResult>("/api/v2/integrations/repair", {
    method: "POST",
  });
}