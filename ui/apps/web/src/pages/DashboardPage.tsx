import {
  getSystemHealth,
  getSystemStatus,
  listJobs,
  runPipeline,
} from "@apxv/api-client";
import {
  ActionGroup,
  Alert,
  AlertDescription,
  Button,
  DataSurface,
  SectionHeader,
  Skeleton,
  StatStrip,
  StatusDot,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@apxv/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { ChevronRight } from "lucide-react";
import { useState } from "react";
import { BuildYourPipelineOnRamp } from "../components/BuildYourPipelineOnRamp";
import { PageShell } from "../components/PageShell";
import { JobsTable } from "../components/JobsTable";
import { formatApiError } from "../lib/api-errors";
import { notifyPipelineQueued } from "../lib/jobs-cache";

function runtimeTone(
  status?: string,
  unreachable?: boolean,
): "success" | "warning" | "destructive" | "muted" {
  if (unreachable) return "destructive";
  if (status === "healthy") return "success";
  if (status === "degraded") return "warning";
  return "muted";
}

export function DashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [quickRunError, setQuickRunError] = useState<string | null>(null);

  const quickRunMutation = useMutation({
    mutationFn: () =>
      runPipeline({
        pack: "reference",
        input_text:
          "Contact: jane@example.com, phone (555) 123-4567, SSN 123-45-6789.",
        attest: true,
        async: true,
      }),
    onSuccess: (result) => {
      setQuickRunError(null);
      if (result.mode === "queued" && result.job_id) {
        notifyPipelineQueued(queryClient, result.job_id, {
          pack: "reference",
          attest: true,
        });
        void navigate({ to: "/jobs", search: { id: result.job_id } });
      } else {
        void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      }
    },
    onError: (err) => setQuickRunError(formatApiError(err)),
  });

  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: () => getSystemHealth(),
    refetchInterval: 10_000,
  });

  const statusQuery = useQuery({
    queryKey: ["system", "status", "dashboard"],
    queryFn: () => getSystemStatus(),
    refetchInterval: 15_000,
  });

  const jobsQuery = useQuery({
    queryKey: ["jobs", "recent"],
    queryFn: () => listJobs({ limit: 8 }),
    refetchInterval: 10_000,
  });

  const integrity = healthQuery.data?.integrity;
  const sovereignSetup = healthQuery.data?.sovereign_setup ?? integrity?.sovereign_setup;
  const auditLogs = integrity?.audit_logs ?? {};
  const auditEntries = Object.entries(auditLogs);
  const recentJobs = jobsQuery.data?.items ?? [];
  const totalJobs = jobsQuery.data?.total ?? recentJobs.length;
  const store = statusQuery.data?.store as
    | { artifacts_count?: number; governance_records?: number }
    | undefined;
  const artifactsCount = store?.artifacts_count;

  const runningJobs = recentJobs.filter((j) => j.status === "running").length;
  const failedJobs = recentJobs.filter((j) => j.status === "failed").length;
  const allAuditValid =
    auditEntries.length > 0 && auditEntries.every(([, valid]) => valid);

  const statsLoading = healthQuery.isLoading || statusQuery.isLoading;

  return (
    <PageShell wide className="space-y-10">
      {healthQuery.isError && (
        <Alert variant="destructive">
          <AlertDescription>
            Cannot reach runtime — start the APXV API server on port 8741, then
            refresh. {(healthQuery.error as Error).message}
          </AlertDescription>
        </Alert>
      )}

      <BuildYourPipelineOnRamp />

      <section className="space-y-6">
        {statsLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-[5.5rem] rounded-lg" />
            ))}
          </div>
        ) : (
          <StatStrip
            items={[
              {
                label: "Runtime",
                value: healthQuery.data?.status ? (
                  <span className="capitalize">{healthQuery.data.status}</span>
                ) : (
                  "—"
                ),
                hint: healthQuery.data?.air_gapped
                  ? "Air-gapped deployment"
                  : "Local deployment",
                tone: runtimeTone(healthQuery.data?.status, healthQuery.isError),
              },
              {
                label: "Jobs",
                value: totalJobs,
                hint:
                  runningJobs > 0
                    ? `${runningJobs} running`
                    : failedJobs > 0
                      ? `${failedJobs} failed`
                      : "Pipeline queue",
                tone: failedJobs > 0 ? "warning" : runningJobs > 0 ? "default" : "muted",
              },
              {
                label: "Artifacts",
                value: artifactsCount ?? "—",
                hint: "Stored outputs",
                tone: "muted",
              },
              {
                label: "Integrity",
                value: integrity?.healthy
                  ? sovereignSetup
                    ? "Sovereign"
                    : "Verified"
                  : integrity
                    ? "Issues"
                    : "—",
                hint: sovereignSetup
                  ? "Operator keys + provenance"
                  : integrity?.sovereign_ok === false
                    ? "Run sovereign bootstrap"
                    : "Store and audit chains",
                tone: integrity?.healthy
                  ? "success"
                  : integrity
                    ? "warning"
                    : "muted",
              },
            ]}
          />
        )}

        <ActionGroup className="border-t border-[hsl(var(--divider-subtle))] pt-6">
          <Button
            variant="link"
            onClick={() => quickRunMutation.mutate()}
            disabled={quickRunMutation.isPending}
          >
            {quickRunMutation.isPending ? "Starting…" : "Run reference pipeline"}
          </Button>
          <Button variant="link" asChild>
            <Link to="/pipeline">Open pipeline runner</Link>
          </Button>
          {quickRunError && (
            <p className="w-full text-sm text-[hsl(var(--destructive))]">
              {quickRunError}
            </p>
          )}
        </ActionGroup>
      </section>

      <section className="space-y-4">
        <SectionHeader
          title="Recent jobs"
          action={
            <Button variant="link" size="sm" className="gap-1" asChild>
              <Link to="/jobs" search={{ id: undefined }}>
                View all
                <ChevronRight className="h-3.5 w-3.5" aria-hidden />
              </Link>
            </Button>
          }
        />
        <DataSurface>
          <JobsTable
            jobs={recentJobs}
            isLoading={jobsQuery.isLoading}
            onSelect={(job) => {
              if (job.id) {
                void navigate({ to: "/jobs", search: { id: job.id } });
              }
            }}
            errorMessage={
              jobsQuery.isError ? formatApiError(jobsQuery.error) : null
            }
            emptyAction={
              <Button size="sm" asChild>
                <Link to="/pipeline">Run a pipeline</Link>
              </Button>
            }
          />
        </DataSurface>
      </section>

      {!healthQuery.isLoading && auditEntries.length > 0 && (
        <section className="space-y-4 border-t border-[hsl(var(--divider-subtle))] pt-10">
          <SectionHeader
            title="Audit chains"
            action={
              <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
                <span className="inline-flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
                  <StatusDot tone={allAuditValid ? "success" : "warning"} />
                  {allAuditValid ? "All valid" : "Needs review"}
                </span>
                <Button variant="link" size="sm" className="gap-1" asChild>
                  <Link to="/audit">
                    Open audit explorer
                    <ChevronRight className="h-3.5 w-3.5" aria-hidden />
                  </Link>
                </Button>
              </div>
            }
          />
          <DataSurface>
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Log</TableHead>
                  <TableHead className="text-right">Chain</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {auditEntries.map(([name, valid]) => (
                  <TableRow key={name}>
                    <TableCell className="font-mono text-sm">{name}</TableCell>
                    <TableCell className="text-right">
                      <span className="inline-flex items-center justify-end gap-2 text-sm text-[hsl(var(--muted-foreground))]">
                        <StatusDot tone={valid ? "success" : "destructive"} />
                        {valid ? "Valid" : "Invalid"}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </DataSurface>
        </section>
      )}
    </PageShell>
  );
}