import { apiFetch } from "./http";

export interface ArtifactRow {
  artifact_hash: string;
  name: string;
  written_at: string;
  blob_relpath: string;
  previous_hash?: string;
}

export interface ArtifactListPage {
  items: ArtifactRow[];
  total: number;
  limit: number;
  offset: number;
}

export interface ArtifactSummary {
  artifact_hash: string;
  attestation_id?: string;
  final_status?: string;
  total_redactions?: number;
  governance_decision?: string;
  compliance_policy_id?: string;
  llm_decision?: unknown;
  has_zk?: boolean;
}

export async function listArtifacts(params?: {
  limit?: number;
  offset?: number;
  name_prefix?: string;
}): Promise<ArtifactListPage> {
  const query = new URLSearchParams();
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));
  if (params?.name_prefix) query.set("name_prefix", params.name_prefix);
  const suffix = query.size ? `?${query}` : "";
  return apiFetch<ArtifactListPage>(`/api/v2/artifacts${suffix}`);
}

export async function getArtifact(hash: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(
    `/api/v2/artifacts/${encodeURIComponent(hash)}`,
  );
}

export async function getArtifactSummary(
  hash: string,
): Promise<ArtifactSummary> {
  return apiFetch<ArtifactSummary>(
    `/api/v2/artifacts/${encodeURIComponent(hash)}/summary`,
  );
}