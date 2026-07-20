/** APXV composition pipelines API (Workshop v1.5+ / operator v1.6). */

import { apiFetch } from "./http";

export interface PipelineStep {
  id: string;
  name: string;
  uses: string;
  description?: string;
  config?: Record<string, unknown>;
  capabilities_required?: string[];
  on_failure?: "stop" | "continue";
  timeout_seconds?: number;
  pack_profile?: string;
  when?: string;
  next_on_success?: string;
  next_on_failure?: string;
  layout?: { x?: number; y?: number };
  /** When false, runner skips the step (Workshop toggle). Default true. */
  enabled?: boolean;
  /**
   * Packs attached to this agent step (ordered).
   * Runner uses pack_profile (primary); first attached syncs to pack_profile on save.
   */
  attached_packs?: string[];
}

export interface PipelineEdge {
  id?: string;
  from: string;
  to: string;
  /** success | failure | always */
  kind?: string;
  /** Optional port id: in | out | out2 | fail */
  port?: string;
}

export interface PipelineDocument {
  apiVersion: string;
  kind: string;
  id: string;
  name: string;
  version: string;
  description?: string;
  metadata?: Record<string, unknown>;
  defaults?: {
    attest?: boolean;
    on_step_failure?: "stop" | "continue";
    /** Promoted Proof Studio profile id (APXV-PROOF-*) */
    proof_profile?: string;
  };
  requires_apxv?: string;
  steps: PipelineStep[];
  /** Freeform wires between steps (Workshop visual board). */
  edges?: PipelineEdge[];
}

export interface PipelineListItem {
  id: string;
  name?: string;
  version?: string;
  description?: string;
  step_count?: number;
  path?: string;
  valid?: boolean;
  errors?: string[];
}

export interface PipelineTemplateInfo {
  id: string;
  name?: string;
  version?: string;
  description?: string;
  step_count?: number;
  maturity?: string;
  path?: string;
}

export interface RunTraceStep {
  step_id: string;
  name?: string;
  uses?: string;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
  error?: string | null;
  artifact_refs?: Array<Record<string, unknown>>;
  summary?: Record<string, unknown>;
}

export interface PipelineRunTrace {
  pipeline_id: string;
  pipeline_version?: string;
  steps: RunTraceStep[];
  final_status: string;
  attest?: {
    requested?: boolean;
    completed?: boolean;
    error?: string;
  };
}

export async function listPipelines(): Promise<{ pipelines: PipelineListItem[] }> {
  return apiFetch<{ pipelines: PipelineListItem[] }>("/api/v2/pipelines");
}

export async function getPipeline(
  id: string,
): Promise<{ pipeline: PipelineDocument }> {
  return apiFetch<{ pipeline: PipelineDocument }>(
    `/api/v2/pipelines/${encodeURIComponent(id)}`,
  );
}

export async function savePipeline(body: {
  pipeline: PipelineDocument;
  format?: "yaml" | "json";
  overwrite?: boolean;
}): Promise<{
  message: string;
  pipeline: PipelineDocument;
  path: string;
  warnings?: string[];
}> {
  return apiFetch("/api/v2/pipelines", {
    method: "POST",
    body,
  });
}

export async function validatePipeline(pipeline: PipelineDocument): Promise<{
  ok: boolean;
  errors: string[];
  warnings: string[];
  pipeline?: PipelineDocument;
}> {
  return apiFetch("/api/v2/pipelines/validate", {
    method: "POST",
    body: { pipeline },
  });
}

export async function importPipeline(body: {
  content: string;
  format?: string;
  overwrite?: boolean;
}): Promise<{
  message: string;
  document: PipelineDocument;
  path: string;
}> {
  return apiFetch("/api/v2/pipelines/import", {
    method: "POST",
    body,
  });
}

export async function exportPipeline(
  id: string,
  format: "yaml" | "json" = "yaml",
): Promise<{ pipeline_id: string; format: string; content: string }> {
  return apiFetch(
    `/api/v2/pipelines/${encodeURIComponent(id)}/export?format=${format}`,
  );
}

export async function deletePipeline(
  id: string,
): Promise<{ message: string; id: string }> {
  return apiFetch(`/api/v2/pipelines/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export async function listPipelineTemplates(): Promise<{
  templates: PipelineTemplateInfo[];
}> {
  return apiFetch("/api/v2/pipelines/templates");
}

export async function getPipelineTemplate(
  id: string,
): Promise<{ template: PipelineTemplateInfo; content: string; pipeline?: PipelineDocument }> {
  return apiFetch(
    `/api/v2/pipelines/templates/${encodeURIComponent(id)}`,
  );
}

export async function runCompositionPipeline(body: {
  pipeline_id: string;
  input_text?: string;
  upload_id?: string;
  attest?: boolean;
  proof_profile?: string;
  async?: boolean;
  llm?: { backend?: string; model?: string; max_latency_ms?: number };
}): Promise<
  | { mode: "queued"; id?: string; job_id?: string; message?: string; [k: string]: unknown }
  | { mode: "complete"; message?: string; result: Record<string, unknown> }
> {
  const { pipeline_id, async: runAsync = true, ...rest } = body;
  const config = await import("./configure").then((m) => m.getApiConfig());
  const base = config.baseUrl.replace(/\/$/, "");
  const { authHeaders, notifyUnauthorized } = await import("./configure");
  const { resolveFetch } = await import("./platform-fetch");
  const { ApiError } = await import("./http");

  const url = `${base}/api/v2/pipelines/${encodeURIComponent(pipeline_id)}/run`;
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Content-Type": "application/json",
    ...authHeaders(config.apiKey),
  };
  const fetchImpl = await resolveFetch();
  const response = await fetchImpl(url, {
    method: "POST",
    headers,
    body: JSON.stringify({ ...rest, async: runAsync }),
  });
  const text = await response.text();
  let payload: Record<string, unknown> = {};
  if (text) {
    try {
      payload = JSON.parse(text) as Record<string, unknown>;
    } catch {
      payload = { message: text };
    }
  }
  if (!response.ok) {
    if (response.status === 401) notifyUnauthorized();
    throw new ApiError(response.status, {
      error: String(payload.error ?? "pipeline_failed"),
      message: String(payload.message ?? text),
      details: payload.details as Record<string, unknown> | undefined,
    });
  }
  if (response.status === 202) {
    return { mode: "queued", ...payload };
  }
  return {
    mode: "complete",
    message: String(payload.message ?? "pipeline complete"),
    result: (payload.result as Record<string, unknown>) ?? payload,
  };
}
