import {
  getJob,
  listJobs,
  runPipeline,
  type Job,
  type PipelineRunRequest,
} from "@apxv/api-client";
import {
  ActionGroup,
  PageToolbar,
  Alert,
  AlertDescription,
  AlertTitle,
  Button,
  DataSurface,
  EmptyState,
  SectionHeader,
  Select,
  Skeleton,
  StatusDot,
} from "@apxv/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { JobDetailPanel } from "../components/JobDetailPanel";
import { JobsTable } from "../components/JobsTable";
import { PageShell } from "../components/PageShell";
import { formatApiError } from "../lib/api-errors";
import { truncateId } from "../lib/format-id";
import { useJobStream } from "../hooks/useJobStream";

export function JobsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { id: selectedId } = useSearch({ from: "/shell/jobs" });
  const [statusFilter, setStatusFilter] = useState<Job["status"] | "">("");
  const [retryError, setRetryError] = useState<string | null>(null);
  const { connected, error: streamError, events } = useJobStream(true);
  const lastEvent = events[events.length - 1];

  useEffect(() => {
    if (lastEvent) {
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      if (selectedId === lastEvent.job_id) {
        void queryClient.invalidateQueries({
          queryKey: ["jobs", "detail", selectedId],
        });
      }
    }
  }, [lastEvent, queryClient, selectedId]);

  const jobsQuery = useQuery({
    queryKey: ["jobs", statusFilter],
    queryFn: () =>
      listJobs({
        limit: 50,
        status: statusFilter || undefined,
      }),
    refetchInterval: connected ? false : 5000,
  });

  const detailQuery = useQuery({
    queryKey: ["jobs", "detail", selectedId],
    queryFn: () => getJob(selectedId!),
    enabled: Boolean(selectedId),
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status === "queued" || status === "running" ? 2000 : false;
    },
  });

  const retryMutation = useMutation({
    mutationFn: async (job: Job) => {
      const payload = job.payload as Record<string, unknown> | undefined;
      if (!payload) throw new Error("Job has no payload to retry.");
      const pack =
        typeof payload.pack === "string" && payload.pack.trim()
          ? payload.pack
          : "apxv-pack-reference-redaction";
      return runPipeline({
        pack,
        input_text: payload.input_text as string | undefined,
        input_files: payload.upload_id
          ? [String(payload.upload_id)]
          : undefined,
        attest: Boolean(payload.attest),
        llm: payload.llm as PipelineRunRequest["llm"],
        async: true,
      });
    },
    onSuccess: (result) => {
      setRetryError(null);
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      if (result.mode === "queued" && result.job_id) {
        void navigate({ to: "/jobs", search: { id: result.job_id } });
      }
    },
    onError: (err) => setRetryError(formatApiError(err)),
  });

  const jobs = jobsQuery.data?.items ?? [];

  return (
    <PageShell wide className="space-y-10">
      <PageToolbar>
        <span className="inline-flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
          <StatusDot tone={connected ? "success" : "muted"} pulse={connected} />
          {connected ? "Live updates" : "Connecting…"}
          {streamError && (
            <span className="text-[hsl(var(--destructive))]">· {streamError}</span>
          )}
        </span>
        <ActionGroup>
          <Select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as Job["status"] | "")
            }
            aria-label="Filter jobs by status"
          >
            <option value="">All statuses</option>
            <option value="queued">Queued</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </Select>
          <Button variant="link" size="sm" onClick={() => jobsQuery.refetch()}>
            Refresh
          </Button>
        </ActionGroup>
      </PageToolbar>

      <div className="grid min-w-0 gap-8 xl:grid-cols-5 xl:gap-10">
        <section className="min-w-0 space-y-4 xl:col-span-3">
          <SectionHeader title="Job queue" />
          {retryError && (
            <Alert variant="destructive">
              <AlertTitle>Retry failed</AlertTitle>
              <AlertDescription>{retryError}</AlertDescription>
            </Alert>
          )}
          <DataSurface>
            <JobsTable
              jobs={jobs}
              selectedId={selectedId}
              onSelect={(job) => {
                if (job.id) {
                  void navigate({ to: "/jobs", search: { id: job.id } });
                }
              }}
              isLoading={jobsQuery.isLoading}
              errorMessage={
                jobsQuery.isError ? formatApiError(jobsQuery.error) : null
              }
              onRetry={(job) => retryMutation.mutate(job)}
              retryingId={
                retryMutation.isPending ? retryMutation.variables?.id : null
              }
            />
          </DataSurface>
        </section>

        <section className="min-w-0 space-y-4 border-t border-[hsl(var(--divider))] pt-6 xl:col-span-2 xl:border-l xl:border-t-0 xl:pl-10 xl:pt-0">
          <SectionHeader
            title="Job detail"
            action={
              selectedId ? (
                <span
                  className="max-w-[12rem] truncate font-mono text-sm text-[hsl(var(--muted-foreground))] sm:max-w-xs"
                  title={selectedId}
                >
                  {truncateId(selectedId, 12, 6)}
                </span>
              ) : undefined
            }
          />
          {!selectedId && (
            <EmptyState
              title="No job selected"
              description="Select a job from the queue to review attestation, redactions, and artifacts."
            />
          )}
          {selectedId && detailQuery.isLoading && (
            <div className="space-y-3">
              <Skeleton className="h-6 w-2/3" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
            </div>
          )}
          {selectedId && detailQuery.isError && (
            <Alert variant="destructive">
              <AlertDescription>{formatApiError(detailQuery.error)}</AlertDescription>
            </Alert>
          )}
          {detailQuery.data && (
            <JobDetailPanel
              job={detailQuery.data}
              onRetry={(job) => retryMutation.mutate(job)}
              retrying={retryMutation.isPending}
            />
          )}
        </section>
      </div>
    </PageShell>
  );
}