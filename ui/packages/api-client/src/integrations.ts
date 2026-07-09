import { apiFetch } from "./http";
import type { OllamaStatus } from "./generated/types.gen";

export type { OllamaStatus };

export async function getOllamaStatus(): Promise<OllamaStatus> {
  return apiFetch<OllamaStatus>("/api/v2/integrations/ollama");
}