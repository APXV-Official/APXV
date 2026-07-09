import {
  listArtifacts,
  verifyAttestation,
  type VerificationReport,
} from "@apxv/api-client";
import {
  ActionGroup,
  Alert,
  AlertDescription,
  Button,
  Checkbox,
  Input,
  Label,
  SectionHeader,
  Skeleton,
  StatusDot,
} from "@apxv/ui";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearch } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { PageShell } from "../components/PageShell";
import { VerificationReportView } from "../components/VerificationReportView";
import { formatApiError } from "../lib/api-errors";
import { truncateId } from "../lib/format-id";

export function VerifyPage() {
  const { hash: hashFromUrl } = useSearch({ from: "/shell/verify" });
  const [artifactHash, setArtifactHash] = useState(hashFromUrl ?? "");

  useEffect(() => {
    if (hashFromUrl) setArtifactHash(hashFromUrl);
  }, [hashFromUrl]);

  const [realZk, setRealZk] = useState(true);
  const [report, setReport] = useState<VerificationReport | null>(null);

  const artifactsQuery = useQuery({
    queryKey: ["artifacts", "verify-picker"],
    queryFn: () => listArtifacts({ limit: 50 }),
  });

  const verifyMutation = useMutation({
    mutationFn: () =>
      verifyAttestation({
        artifact_hash: artifactHash.trim(),
        real_zk: realZk,
      }),
    onSuccess: (data) => setReport(data),
  });

  const attestedArtifacts = (artifactsQuery.data?.items ?? []).filter((a) =>
    a.name.toLowerCase().includes("attest"),
  );

  return (
    <PageShell className="mx-auto max-w-3xl space-y-10">
      <SectionHeader title="Attestation verifier" />

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

      {artifactsQuery.isLoading ? (
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-9 w-28 rounded-lg" />
          ))}
        </div>
      ) : attestedArtifacts.length > 0 ? (
        <section className="space-y-3 border-t border-[hsl(var(--divider))] pt-8">
          <Label>Recent attested artifacts</Label>
          <ActionGroup>
            {attestedArtifacts.slice(0, 8).map((row) => (
              <Button
                key={row.artifact_hash}
                variant="link"
                size="sm"
                onClick={() => setArtifactHash(row.artifact_hash)}
              >
                {row.name.slice(0, 20)}
                <span className="ml-1 font-mono text-xs opacity-60">
                  {truncateId(row.artifact_hash, 6, 4)}
                </span>
              </Button>
            ))}
          </ActionGroup>
        </section>
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
          </ActionGroup>
          <VerificationReportView report={report} embedded />
        </section>
      )}
    </PageShell>
  );
}