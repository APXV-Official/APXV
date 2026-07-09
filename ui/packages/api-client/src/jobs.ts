import { apiFetch } from "./http";
import type { Job } from "./generated/types.gen";

export type { Job };

type RawJob = Job & { job_type?: string };

function normalizeJob(raw: RawJob): Job {
  const type = raw.type ?? raw.job_type;
  return type ? { ...raw, type } : raw;
}

export interface JobListResponse {
  items: Job[];
  total?: number;
  limit?: number;
  offset?: number;
}

export async function listJobs(params?: {
  limit?: number;
  status?: Job["status"];
}): Promise<JobListResponse> {
  const query = new URLSearchParams();
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.status) query.set("status", params.status);
  const suffix = query.size ? `?${query}` : "";
  const data = await apiFetch<JobListResponse & { jobs?: RawJob[] }>(
    `/api/v2/jobs${suffix}`,
  );
  const rawItems = data.items ?? data.jobs ?? [];
  return {
    ...data,
    items: rawItems.map((job) => normalizeJob(job as RawJob)),
  };
}

export async function getJob(id: string): Promise<Job> {
  const raw = await apiFetch<RawJob>(`/api/v2/jobs/${encodeURIComponent(id)}`);
  return normalizeJob(raw);
}