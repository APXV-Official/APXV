import { authHeaders, getApiConfig, notifyUnauthorized } from "./configure";
import { ApiError } from "./http";
import type {
  JobQueued,
  PipelineRunRequest as GeneratedPipelineRunRequest,
  PipelineRunResponse,
} from "./generated/types.gen";

export type { PipelineRunResponse, JobQueued };

/** Pack may be built-in alias or full apxv-pack-* id. */
export type PipelineRunRequest = Omit<GeneratedPipelineRunRequest, "pack"> & {
  pack?: string;
};

export type PipelineRunResult =
  | ({ mode: "queued" } & JobQueued)
  | ({ mode: "complete" } & PipelineRunResponse);

export async function runPipeline(
  body: PipelineRunRequest,
): Promise<PipelineRunResult> {
  const config = getApiConfig();
  const base = config.baseUrl.replace(/\/$/, "");
  const url = `${base}/api/v2/pipeline/run`;

  const headers: Record<string, string> = {
    Accept: "application/json",
    "Content-Type": "application/json",
    ...authHeaders(config.apiKey),
  };

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
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
    return { mode: "queued", ...(payload as JobQueued) };
  }
  return { mode: "complete", ...(payload as PipelineRunResponse) };
}