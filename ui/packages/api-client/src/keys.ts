import { apiFetch } from "./http";
import type { ApiKeyCreated, ApiKeyMeta } from "./generated/types.gen";

export type { ApiKeyMeta, ApiKeyCreated };

export async function listApiKeys(): Promise<{ keys: ApiKeyMeta[] }> {
  return apiFetch<{ keys: ApiKeyMeta[] }>("/api/v2/keys");
}

export async function createApiKey(body: {
  id: string;
  description?: string;
  role?: string;
}): Promise<ApiKeyCreated> {
  return apiFetch<ApiKeyCreated>("/api/v2/keys", {
    method: "POST",
    body,
  });
}

export async function revokeApiKey(id: string): Promise<{ message: string; id: string }> {
  return apiFetch(`/api/v2/keys/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}