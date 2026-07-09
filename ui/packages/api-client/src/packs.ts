import { apiFetch } from "./http";

export interface CreatePackRequest {
  pack_id: string;
  name: string;
  description?: string;
  template?: "reference" | "minimal";
}

export interface CreatePackResponse {
  message: string;
  pack: {
    pack_id: string;
    name: string;
    path: string;
    template: string;
  };
}

export interface PackInfo {
  id: string;
  name: string;
  version: string;
  description: string;
  requires_apxv1?: string;
  official?: boolean;
  path?: string;
  demo?: string;
  readme_excerpt?: string;
  governance_files?: string[];
  agents?: Array<{ id: string; type?: string; module?: string }>;
}

export interface ActivePackRecord {
  pack_id: string;
  activated_at?: string;
  activated_by?: string;
  governance_summary_hash?: string;
}

export interface ActivePackResponse {
  active: ActivePackRecord | null;
  pack: PackInfo | null;
}

export interface ActivatePackRequest {
  confirm?: boolean;
  activated_by?: string;
}

export interface ActivatePackResponse {
  message: string;
  pack_id: string;
  active: ActivePackRecord;
  snapshot_of?: string | null;
}

export interface ClonePackRequest {
  pack_id: string;
  name: string;
  description?: string;
}

export interface ClonePackResponse {
  message: string;
  pack: {
    pack_id: string;
    name: string;
    source_pack_id?: string;
    path?: string;
  };
}

export async function listPacks(): Promise<{ packs: PackInfo[] }> {
  return apiFetch<{ packs: PackInfo[] }>("/api/v2/packs");
}

export async function getPack(id: string): Promise<PackInfo> {
  return apiFetch<PackInfo>(`/api/v2/packs/${encodeURIComponent(id)}`);
}

export async function createPack(
  body: CreatePackRequest,
): Promise<CreatePackResponse> {
  return apiFetch<CreatePackResponse>("/api/v2/packs", {
    method: "POST",
    body,
  });
}

export async function getActivePack(): Promise<ActivePackResponse> {
  return apiFetch<ActivePackResponse>("/api/v2/packs/active");
}

export async function activatePack(
  id: string,
  body: ActivatePackRequest = {},
): Promise<ActivatePackResponse> {
  return apiFetch<ActivatePackResponse>(
    `/api/v2/packs/${encodeURIComponent(id)}/activate`,
    { method: "POST", body },
  );
}

export async function clonePack(
  sourceId: string,
  body: ClonePackRequest,
): Promise<ClonePackResponse> {
  return apiFetch<ClonePackResponse>(
    `/api/v2/packs/${encodeURIComponent(sourceId)}/clone`,
    { method: "POST", body },
  );
}