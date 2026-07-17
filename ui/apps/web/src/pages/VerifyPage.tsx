import {
  getJob,
  listArtifacts,
  listJobs,
  verifyAttestation,
  type VerificationReport,
} from "@apxv/api-client";
import {
  ActionGroup,
  Alert,
  AlertDescription,
  Button,
  Checkbox,
  EmptyState,
  Input,
  Label,
  SectionHeader,
  Skeleton,
  StatusDot,
} from "@apxv/ui";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { PageShell } from "../components/PageShell";
import { VerificationReportView } from "../components/VerificationReportView";
import { formatApiError } from "../lib/api-errors";
import { truncateId } from "../lib/format-id";
import { artifactHashFromJob } from "../lib/pipeline-result";
import { PACK_TUTORIAL_URL } from "../lib/pack-studio";

export function VerifyPage() {
  const navigate = useNavigate();
  const { hash: hashFromUrl, job: jobFromUrl } = useSearch({
    from: "/shell/verify",
  });
  const [artifactHash, setArtifactHash] = useState(hashFromUrl ?? "");
  const [realZk, setRealZk] = useState(true);
  const [report, setReport] = useState<VerificationReport | null>(null);

  const jobQuery = useQuery({
    queryKey: ["jobs", "verify-context", jobFromUrl],
    queryFn: () => getJob(jobFromUrl!),
    enabled: Boolean(jobFromUrl),
  });

  const recentJobsQuery = useQuery({
    queryKey: ["jobs", "verify-recent"],
    queryFn: () => listJobs({ limit: 20, status: "completed" }),
  });

  const artifactsQuery = useQuery({
    queryKey: ["artifacts", "verify-picker"],
    queryFn: () => listArtifacts({ limit: 50, name_prefix: "attest" }),
  });

  const verifyMutation = useMutation({
    mutationFn: () =>
      verifyAttestation({
        artifact_hash: artifactHash.trim(),
        real_zk: realZk,
      }),
    onSuccess: (data) => setReport(data),
  });

  const jobsWithArtifacts = useMemo(() => {
    const items = recentJobsQuery.data?.items ?? [];
    return items.filter((job) => artifactHashFromJob(job));
  }, [recentJobsQuery.data?.items]);

  const attestedArtifacts = artifactsQuery.data?.items ?? [];

  useEffect(() => {
    if (hashFromUrl) setArtifactHash(hashFromUrl);
  }, [hashFromUrl]);

  useEffect(() => {
    if (hashFromUrl || !jobFromUrl || !jobQuery.data) return;
    const hash = artifactHashFromJob(jobQuery.data);
    if (hash) {
      setArtifactHash(hash);
      void navigate({
        to: "/verify",
        search: { hash, job: jobFromUrl },
        replace: true,
      });
    }
  }, [hashFromUrl, jobFromUrl, jobQuery.data, navigate]);

  function selectArtifactHash(hash: string, jobId?: string) {
    setArtifactHash(hash);
    setReport(null);
    void navigate({
      to: "/verify",
      search: {
        hash,
        job: jobId ?? undefined,
      },
    });
  }

  return (
    <PageShell className="mx-auto max-w-3xl space-y-10">
      <SectionHeader title="Attestation verifier" />

      {jobFromUrl && (
        <Alert>
          <AlertDescription className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <span>
              Opened from job{" "}
              <span className="font-mono text-xs">{truncateId(jobFromUrl)}</span>
            </span>
            <Button variant="link" size="sm" className="h-auto p-0" asChild>
              <Link to="/jobs" search={{ id: jobFromUrl }}>
                View job
              </Link>
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {jobFromUrl && jobQuery.isError && (
        <Alert variant="destructive">
          <AlertDescription>{formatApiError(jobQuery.error)}</AlertDescription>
        </Alert>
      )}

      <section className="space-y-3">
        <Label htmlFor="artifact-hash">Artifact hash</Label>
        <Input
          id="artifact-hash"
          value={artifactHash}
          onChange={(e) => setArtifactHash(e.target.value)}
          placeholder="Paste artifact hash or pick below"
          className="font-mono"
        />
      </section>

      {recentJobsQuery.isError && (
        <Alert variant="destructive">
          <AlertDescription className="space-y-3">
            <p>{formatApiError(recentJobsQuery.error)}</p>
            <Button
              variant="link"
              size="sm"
              className="h-auto p-0"
              onClick={() => void recentJobsQuery.refetch()}
            >
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {recentJobsQuery.isLoading ? (
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-9 w-36 rounded-lg" />
          ))}
        </div>
      ) : jobsWithArtifacts.length > 0 ? (
        <section className="space-y-3 border-t border-[hsl(var(--divider))] pt-8">
          <Label>Recent completed jobs with artifacts</Label>
          <ActionGroup className="flex-wrap">
            {jobsWithArtifacts.slice(0, 8).map((job) => {
              const hash = artifactHashFromJob(job)!;
              return (
                <Button
                  key={job.id}
                  variant="link"
                  size="sm"
                  onClick={() => selectArtifactHash(hash, job.id)}
                >
                  {truncateId(job.id ?? "job")}
                  <span className="ml-1 font-mono text-xs opacity-60">
                    {truncateId(hash, 6, 4)}
                  </span>
                </Button>
              );
            })}
          </ActionGroup>
        </section>
      ) : null}

      {artifactsQuery.isLoading ? (
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-9 w-28 rounded-lg" />
          ))}
        </div>
      ) : artifactsQuery.isError ? (
        <Alert variant="destructive">
          <AlertDescription>
            {formatApiError(artifactsQuery.error)}
          </AlertDescription>
        </Alert>
      ) : attestedArtifacts.length > 0 ? (
        <section className="space-y-3 border-t border-[hsl(var(--divider))] pt-8">
          <Label>Recent attested artifacts</Label>
          <ActionGroup className="flex-wrap">
            {attestedArtifacts.slice(0, 8).map((row) => (
              <Button
                key={row.artifact_hash}
                variant="link"
                size="sm"
                onClick={() => selectArtifactHash(row.artifact_hash)}
              >
                {row.name.slice(0, 20)}
                <span className="ml-1 font-mono text-xs opacity-60">
                  {truncateId(row.artifact_hash, 6, 4)}
                </span>
              </Button>
            ))}
          </ActionGroup>
        </section>
      ) : !recentJobsQuery.isLoading && jobsWithArtifacts.length === 0 ? (
        <EmptyState
          title="No attested artifacts yet"
          description="Run a pipeline with attestation enabled, then open the artifact from Jobs or pick it here."
          action={
            <ActionGroup>
              <Button size="sm" asChild>
                <Link to="/pipeline">Run a pipeline</Link>
              </Button>
              <Button variant="link" size="sm" asChild>
                <a
                  href={PACK_TUTORIAL_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  BUILD-YOUR-FIRST-PACK guide
                </a>
              </Button>
            </ActionGroup>
          }
        />
      ) : null}

      <section className="space-y-4 border-t border-[hsl(var(--divider))] pt-8">
        <Checkbox
          id="real-zk"
          checked={realZk}
          onChange={(e) => setRealZk(e.target.checked)}
          label="Run independent Groth16 verification"
        />

        <ActionGroup>
          <Button
            onClick={() => verifyMutation.mutate()}
            disabled={!artifactHash.trim() || verifyMutation.isPending}
          >
            {verifyMutation.isPending ? "Verifying…" : "Verify attestation"}
          </Button>
        </ActionGroup>

        {verifyMutation.isError && (
          <Alert variant="destructive">
            <AlertDescription>{formatApiError(verifyMutation.error)}</AlertDescription>
          </Alert>
        )}
      </section>

      {report && (
        <section className="space-y-4 border-t border-[hsl(var(--divider))] pt-8">
          <ActionGroup>
            <span className="inline-flex items-center gap-2 text-sm font-medium">
              <StatusDot tone={report.overall_valid ? "success" : "destructive"} />
              {report.overall_valid ? "Verification passed" : "Verification failed"}
            </span>
            {jobFromUrl && (
              <Button variant="link" size="sm" asChild>
                <Link to="/jobs" search={{ id: jobFromUrl }}>
                  View originating job
                </Link>
              </Button>
            )}
          </ActionGroup>
          <VerificationReportView report={report} embedded />
        </section>
      )}
    </PageShell>
  );
}