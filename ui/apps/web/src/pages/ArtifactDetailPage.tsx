import {
  getArtifact,
  getArtifactSummary,
  verifyAttestation,
  type VerificationReport,
} from "@apxv/api-client";
import {
  ActionGroup,
  Alert,
  AlertDescription,
  Badge,
  Button,
  PageToolbar,
  Skeleton,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@apxv/ui";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useParams } from "@tanstack/react-router";
import { useState } from "react";
import { PageShell } from "../components/PageShell";
import { VerificationReportView } from "../components/VerificationReportView";
import { formatApiError } from "../lib/api-errors";
import { truncateId } from "../lib/format-id";
import { ZkProofVisualizer } from "../components/ZkProofVisualizer";
import { extractArtifactZkNodes } from "../lib/zk-utils";

function extractRedactions(data: Record<string, unknown>): unknown[] {
  const artifact = (data.artifact ?? data) as Record<string, unknown>;
  const proposed = (artifact.proposed_artifact ?? {}) as Record<string, unknown>;
  const output = (proposed.output ?? {}) as Record<string, unknown>;
  const redactions = output.redactions ?? output.redactions_applied;
  return Array.isArray(redactions) ? redactions : [];
}

export function ArtifactDetailPage() {
  const { hash } = useParams({ from: "/shell/artifacts/$hash" });
  const [verifyReport, setVerifyReport] = useState<VerificationReport | null>(
    null,
  );

  const summaryQuery = useQuery({
    queryKey: ["artifacts", hash, "summary"],
    queryFn: () => getArtifactSummary(hash),
  });

  const artifactQuery = useQuery({
    queryKey: ["artifacts", hash],
    queryFn: () => getArtifact(hash),
  });

  const verifyMutation = useMutation({
    mutationFn: () =>
      verifyAttestation({ artifact_hash: hash, real_zk: true }),
    onMutate: () => setVerifyReport(null),
    onSuccess: (data) => setVerifyReport(data),
  });

  const data = artifactQuery.data;
  const summary = summaryQuery.data;
  const redactions = data ? extractRedactions(data) : [];
  const zkNodes = data ? extractArtifactZkNodes(data) : [];
  const hasArtifact = Boolean(data);

  return (
    <PageShell className="mx-auto max-w-4xl space-y-10">
      <PageToolbar>
        <ActionGroup>
          <Button variant="link" size="sm" asChild>
            <Link to="/artifacts">← Library</Link>
          </Button>
          <Button variant="link" size="sm" asChild>
            <Link to="/verify" search={{ hash }}>
              Open in verifier
            </Link>
          </Button>
        </ActionGroup>
        <span
          className="font-mono text-sm text-[hsl(var(--muted-foreground))]"
          title={hash}
        >
          {truncateId(hash, 16, 12)}
        </span>
      </PageToolbar>

      {(summaryQuery.isLoading || artifactQuery.isLoading) && (
        <div className="space-y-2">
          <Skeleton className="h-6 w-1/3" />
          <Skeleton className="h-24 w-full" />
        </div>
      )}

      {artifactQuery.isError && (
        <Alert variant="destructive">
          <AlertDescription>{formatApiError(artifactQuery.error)}</AlertDescription>
        </Alert>
      )}

      {hasArtifact && (
        <Tabs defaultValue={summary ? "summary" : "raw"}>
          <TabsList>
            <TabsTrigger value="summary">Summary</TabsTrigger>
            <TabsTrigger value="redactions">
              Redactions ({redactions.length})
            </TabsTrigger>
            <TabsTrigger value="zk">ZK ({zkNodes.length})</TabsTrigger>
            <TabsTrigger value="verify">Verify</TabsTrigger>
            <TabsTrigger value="raw">Raw JSON</TabsTrigger>
          </TabsList>

          <TabsContent value="summary" className="space-y-4 pt-6">
            {summaryQuery.isError && (
              <Alert variant="warning">
                <AlertDescription>
                  Summary unavailable: {(summaryQuery.error as Error).message}
                </AlertDescription>
              </Alert>
            )}
            {summary ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">
                    Final status
                  </p>
                  <Badge className="mt-1">{summary.final_status ?? "—"}</Badge>
                </div>
                <div>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">
                    Attestation ID
                  </p>
                  <p className="mt-1 font-mono text-sm">
                    {summary.attestation_id ?? "—"}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">
                    Redactions
                  </p>
                  <p className="mt-1 text-2xl font-semibold tabular-nums">
                    {summary.total_redactions ?? 0}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">
                    Governance
                  </p>
                  <p className="mt-1">{summary.governance_decision ?? "—"}</p>
                </div>
                <div>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">
                    ZK proofs
                  </p>
                  <Badge variant={summary.has_zk ? "success" : "secondary"} className="mt-1">
                    {summary.has_zk ? "Present" : "None"}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm text-[hsl(var(--muted-foreground))]">
                    Policy
                  </p>
                  <p className="mt-1 font-mono text-sm">
                    {summary.compliance_policy_id ?? "—"}
                  </p>
                </div>
              </div>
            ) : (
              !summaryQuery.isLoading && (
                <p className="text-sm text-[hsl(var(--muted-foreground))]">
                  No summary metadata for this artifact.
                </p>
              )
            )}
          </TabsContent>

          <TabsContent value="redactions" className="pt-6">
            {redactions.length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                No redaction entries in this artifact.
              </p>
            ) : (
              <pre className="max-h-96 overflow-auto rounded-xl bg-[hsl(var(--surface-elevated))] p-4 text-sm">
                {JSON.stringify(redactions, null, 2)}
              </pre>
            )}
          </TabsContent>

          <TabsContent value="zk" className="space-y-4 pt-6">
            <ZkProofVisualizer nodes={zkNodes} />
          </TabsContent>

          <TabsContent value="verify" className="space-y-4 pt-6">
            <ActionGroup>
              <Button
                onClick={() => verifyMutation.mutate()}
                disabled={verifyMutation.isPending}
              >
                {verifyMutation.isPending
                  ? "Running verification…"
                  : "Verify attestation (Python + Groth16)"}
              </Button>
            </ActionGroup>
            {verifyMutation.isError && (
              <Alert variant="destructive">
                <AlertDescription>
                  {formatApiError(verifyMutation.error)}
                </AlertDescription>
              </Alert>
            )}
            {verifyReport && (
              <VerificationReportView report={verifyReport} embedded />
            )}
          </TabsContent>

          <TabsContent value="raw" className="pt-6">
            <pre className="max-h-[32rem] overflow-auto rounded-xl bg-[hsl(var(--surface-elevated))] p-4 text-sm">
              {JSON.stringify(data, null, 2)}
            </pre>
          </TabsContent>
        </Tabs>
      )}
    </PageShell>
  );
}