import type { Job } from "@apxv/api-client";
import type { ReactNode } from "react";
import {
  ActionGroup,
  Badge,
  Button,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@apxv/ui";
import { Link } from "@tanstack/react-router";
import { DetailSection } from "./DetailSection";
import { JobStatusBadge } from "./JobStatusBadge";

interface PipelineResult {
  pack?: string;
  attestation_id?: string;
  final_status?: string;
  governance_decision?: string;
  artifact_hash?: string;
  artifact_path?: string;
  total_redactions?: number;
  full_provenance_hash?: string;
  zk_summary?: {
    governance?: Record<string, boolean>;
    entity?: Record<string, boolean>;
  };
  attested_result?: {
    governance_decision?: { decision?: string; rationale?: string };
    proposed_artifact?: {
      output?: {
        redacted_text?: string;
        redactions_applied?: Array<{ category: string; count: number }>;
        entities?: Array<{
          type: string;
          severity?: string;
          category?: string;
          redacted_as?: string;
        }>;
      };
    };
    agent_chain?: string[];
  };
}

function parseResult(job: Job): PipelineResult | null {
  if (!job.result || typeof job.result !== "object") return null;
  return job.result as PipelineResult;
}

function governanceVariant(
  decision?: string,
): "success" | "warning" | "destructive" | "secondary" {
  if (!decision) return "secondary";
  if (decision.includes("REJECT") || decision.includes("DENY")) {
    return "destructive";
  }
  if (decision.includes("REVIEW")) return "warning";
  if (decision.includes("APPROVED") || decision === "ATTESTED") return "success";
  return "secondary";
}

function ZkSummaryBadges({ summary }: { summary: Record<string, boolean> }) {
  const allValid = Object.values(summary).every(Boolean);
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-3">
        {Object.entries(summary).map(([name, valid]) => (
          <Badge key={name} variant={valid ? "success" : "destructive"}>
            {name.replace(/_/g, "-")}
          </Badge>
        ))}
      </div>
      <p className="text-sm text-[hsl(var(--muted-foreground))]">
        {allValid ? "All proofs verified" : "One or more proofs failed"}
      </p>
    </div>
  );
}

function truncateHash(hash: string, head = 12, tail = 8) {
  if (hash.length <= head + tail + 3) return hash;
  return `${hash.slice(0, head)}…${hash.slice(-tail)}`;
}

function DetailRow({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <span className="shrink-0 text-sm text-[hsl(var(--muted-foreground))]">{label}</span>
      <span className="min-w-0 text-right text-sm text-[hsl(var(--foreground))]">{children}</span>
    </div>
  );
}

export function JobDetailPanel({
  job,
  onRetry,
  retrying,
}: {
  job: Job;
  onRetry?: (job: Job) => void;
  retrying?: boolean;
}) {
  const payload = job.payload as Record<string, unknown> | undefined;
  const result = parseResult(job);
  const pack =
    (payload?.pack as string | undefined) ?? result?.pack ?? "—";
  const inputText = payload?.input_text as string | undefined;
  const attest = Boolean(payload?.attest);
  const artifactHash = result?.artifact_hash;
  const redactedText =
    result?.attested_result?.proposed_artifact?.output?.redacted_text;
  const redactions =
    result?.attested_result?.proposed_artifact?.output?.redactions_applied;
  const entities =
    result?.attested_result?.proposed_artifact?.output?.entities;
  const governance =
    result?.governance_decision ??
    result?.attested_result?.governance_decision?.decision;
  const rationale = result?.attested_result?.governance_decision?.rationale;
  const agents = result?.attested_result?.agent_chain ?? [];

  return (
    <div className="min-w-0 space-y-5 text-base">
      <DetailRow label="Status">
        <JobStatusBadge status={job.status} />
      </DetailRow>

      {job.error && (
        <div className="rounded-lg bg-[hsl(var(--destructive))]/10 px-4 py-3 text-sm text-[hsl(var(--destructive))]">
          {job.error}
        </div>
      )}

      <DetailSection title="Request" defaultOpen>
        <div className="divide-y divide-[hsl(var(--divider-subtle))]">
          <DetailRow label="Pack">
            <span className="font-mono">{pack}</span>
          </DetailRow>
          <DetailRow label="Attestation">{attest ? "Requested" : "Off"}</DetailRow>
        </div>
        {inputText && (
          <div className="mt-4">
            <p className="mb-2 text-sm text-[hsl(var(--muted-foreground))]">Input</p>
            <p className="rounded-lg bg-[hsl(var(--surface-elevated))] p-3 font-mono text-sm leading-relaxed">
              {inputText}
            </p>
          </div>
        )}
      </DetailSection>

      {result && job.status === "completed" && (
        <DetailSection title="Pipeline result">
          <div className="divide-y divide-[hsl(var(--divider-subtle))]">
            <DetailRow label="Outcome">
              <Badge variant="success">{result.final_status ?? "—"}</Badge>
            </DetailRow>
            <DetailRow label="Governance">
              <Badge variant={governanceVariant(governance)} className="max-w-[65%] truncate">
                {governance ?? "—"}
              </Badge>
            </DetailRow>
            <DetailRow label="Redactions">{result.total_redactions ?? 0}</DetailRow>
          </div>

          {rationale && (
            <p className="mt-4 text-sm leading-relaxed text-[hsl(var(--muted-foreground))]">
              {rationale}
            </p>
          )}

          {redactions && redactions.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-3">
              {redactions.map((r) => (
                <Badge key={r.category} variant="secondary">
                  {r.category} ×{r.count}
                </Badge>
              ))}
            </div>
          )}

          {redactedText && (
            <div className="mt-4">
              <p className="mb-2 text-sm font-medium text-[hsl(var(--muted-foreground))]">
                Redacted output
              </p>
              <p className="rounded-lg bg-[hsl(var(--surface-elevated))] p-3 font-mono text-sm leading-relaxed">
                {redactedText}
              </p>
            </div>
          )}

          {entities && entities.length > 0 && (
            <div className="mt-4">
              <p className="mb-2 text-sm text-[hsl(var(--muted-foreground))]">
                Entities detected
              </p>
              <ul className="space-y-1.5">
                {entities.map((entity, i) => (
                  <li
                    key={`${entity.type}-${i}`}
                    className="flex items-center justify-between gap-3 rounded-lg bg-[hsl(var(--surface-elevated))] px-3 py-2 text-sm"
                  >
                    <span className="font-mono">{entity.type}</span>
                    <span className="text-[hsl(var(--muted-foreground))]">
                      {entity.severity ?? entity.category ?? entity.redacted_as}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {agents.length > 0 && (
            <div className="mt-4">
              <p className="mb-2 text-sm text-[hsl(var(--muted-foreground))]">Agent chain</p>
              <div className="flex flex-wrap gap-3">
                {agents.map((id) => (
                  <Badge key={id} variant="secondary">
                    {id}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {result.zk_summary?.governance && (
            <div className="mt-4">
              <p className="mb-2 text-sm text-[hsl(var(--muted-foreground))]">
                ZK governance proofs
              </p>
              <ZkSummaryBadges summary={result.zk_summary.governance} />
            </div>
          )}

          {result.zk_summary?.entity && (
            <div className="mt-4">
              <p className="mb-2 text-sm text-[hsl(var(--muted-foreground))]">
                ZK entity proofs
              </p>
              <ZkSummaryBadges summary={result.zk_summary.entity} />
            </div>
          )}

          {artifactHash && (
            <div className="mt-4 space-y-3 border-t border-[hsl(var(--divider-subtle))] pt-4">
              <p className="font-mono text-sm text-[hsl(var(--muted-foreground))]">
                Artifact {truncateHash(artifactHash)}
              </p>
              <ActionGroup>
                <Button variant="link" size="sm" asChild>
                  <Link to="/artifacts/$hash" params={{ hash: artifactHash }}>
                    Open artifact
                  </Link>
                </Button>
                <Button variant="link" size="sm" asChild>
                  <Link to="/verify" search={{ hash: artifactHash }}>
                    Verify
                  </Link>
                </Button>
              </ActionGroup>
            </div>
          )}

          {result.attestation_id && (
            <p className="mt-3 font-mono text-sm text-[hsl(var(--muted-foreground))]">
              Attestation {result.attestation_id}
            </p>
          )}

          {result.full_provenance_hash && (
            <p className="font-mono text-sm text-[hsl(var(--muted-foreground))]">
              Provenance {truncateHash(result.full_provenance_hash)}
            </p>
          )}
        </DetailSection>
      )}

      {(job.status === "queued" || job.status === "running") && (
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Pipeline in progress — this panel refreshes automatically.
        </p>
      )}

      {job.status === "failed" && onRetry && (
        <ActionGroup>
          <Button
            variant="link"
            disabled={retrying}
            onClick={() => onRetry(job)}
          >
            {retrying ? "Retrying…" : "Retry job"}
          </Button>
        </ActionGroup>
      )}

      <Tabs defaultValue="request">
        <TabsList>
          <TabsTrigger value="request">Request JSON</TabsTrigger>
          <TabsTrigger value="raw">Full payload</TabsTrigger>
        </TabsList>
        <TabsContent value="request" className="pt-3">
          {payload ? (
            <pre className="max-h-48 overflow-auto rounded-xl bg-[hsl(var(--surface-elevated))] p-4 text-sm">
              {JSON.stringify(payload, null, 2)}
            </pre>
          ) : (
            <p className="text-sm text-[hsl(var(--muted-foreground))]">No payload.</p>
          )}
        </TabsContent>
        <TabsContent value="raw" className="space-y-4 pt-3">
          {payload && (
            <div>
              <p className="mb-2 text-sm text-[hsl(var(--muted-foreground))]">Payload</p>
              <pre className="max-h-40 overflow-auto rounded-xl bg-[hsl(var(--surface-elevated))] p-4 text-sm">
                {JSON.stringify(payload, null, 2)}
              </pre>
            </div>
          )}
          {job.result ? (
            <div>
              <p className="mb-2 text-sm text-[hsl(var(--muted-foreground))]">Result</p>
              <pre className="max-h-72 overflow-auto rounded-xl bg-[hsl(var(--surface-elevated))] p-4 text-sm">
                {JSON.stringify(job.result, null, 2)}
              </pre>
            </div>
          ) : (
            <p className="text-sm text-[hsl(var(--muted-foreground))]">No result yet.</p>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}