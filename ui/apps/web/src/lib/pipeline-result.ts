import type { Job } from "@apxv/api-client";

export interface PipelineJobResult {
  pack?: string;
  attestation_id?: string;
  artifact_hash?: string;
  final_status?: string;
}

export function pipelineResultFromJob(job: Job): PipelineJobResult | null {
  if (!job.result || typeof job.result !== "object") return null;
  return job.result as PipelineJobResult;
}

export function artifactHashFromJob(job: Job): string | null {
  const hash = pipelineResultFromJob(job)?.artifact_hash;
  return typeof hash === "string" && hash.trim() ? hash.trim() : null;
}