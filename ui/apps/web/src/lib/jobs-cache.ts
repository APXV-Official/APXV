import type { Job, JobListResponse, JobStreamEvent } from "@apxv/api-client";
import type { QueryClient } from "@tanstack/react-query";

function mergeJob(existing: Job | undefined, incoming: Job): Job {
  if (!existing) return incoming;
  return {
    ...existing,
    ...incoming,
    payload: incoming.payload ?? existing.payload,
    result: incoming.result ?? existing.result,
  };
}

/** Apply a live SSE job event directly into react-query cache (no refetch round-trip). */
export function patchJobsFromStreamEvent(
  queryClient: QueryClient,
  event: JobStreamEvent,
): void {
  const jobId = event.job_id;
  const job = { ...event.job, id: event.job.id ?? jobId };

  queryClient.setQueriesData<JobListResponse>(
    { queryKey: ["jobs"] },
    (old) => {
      if (!old?.items) return old;
      const items = [...old.items];
      const idx = items.findIndex((row) => row.id === jobId);
      if (idx >= 0) {
        items[idx] = mergeJob(items[idx], job);
      } else {
        items.unshift(job);
      }
      return { ...old, items, total: Math.max(old.total ?? items.length, items.length) };
    },
  );

  queryClient.setQueryData<Job>(["jobs", "detail", jobId], (old) =>
    mergeJob(old, job),
  );
}

/** Optimistic row when pipeline returns 202 before SSE catches up. */
export function notifyPipelineQueued(
  queryClient: QueryClient,
  jobId: string,
  payload?: Job["payload"],
): void {
  const now = new Date().toISOString();
  const optimistic: Job = {
    id: jobId,
    type: "pipeline",
    status: "queued",
    payload,
    created_at: now,
    updated_at: now,
  };
  patchJobsFromStreamEvent(queryClient, {
    job_id: jobId,
    status: "queued",
    job: optimistic,
  });
}

export function invalidateJobsQueries(queryClient: QueryClient): void {
  void queryClient.invalidateQueries({ queryKey: ["jobs"] });
}