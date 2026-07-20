import type { PipelineRunTrace, RunTraceStep } from "@apxv/api-client";
import { Badge, Button } from "@apxv/ui";
import { Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { collapseApproveTraceSteps } from "../lib/workshop-pipeline";

function statusVariant(
  status: string,
): "success" | "destructive" | "warning" | "secondary" | "outline" {
  const s = status.toLowerCase();
  if (s === "succeeded") return "success";
  if (s === "failed") return "destructive";
  if (s === "running" || s === "awaiting_approval") return "warning";
  if (s === "skipped" || s === "pending") return "secondary";
  return "outline";
}

function summaryLine(step: RunTraceStep): string | null {
  const s = step.summary || {};
  if (step.error) return step.error;
  if (typeof s.total_redactions === "number") {
    return `${s.total_redactions} redaction(s)`;
  }
  if (typeof s.governance_decision === "string") {
    return String(s.governance_decision);
  }
  if (s.approved === true) return "Approved";
  if (typeof s.message === "string") return s.message;
  if (typeof s.attestation_id === "string") return "Attested";
  if (typeof s.handoff_pipeline_id === "string") {
    return `Handoff → ${s.handoff_pipeline_id}`;
  }
  if (typeof s.reason === "string") return String(s.reason);
  return null;
}

function StepRow({ step }: { step: RunTraceStep }) {
  const [open, setOpen] = useState(Boolean(step.error));
  const line = summaryLine(step);
  return (
    <div className="rounded-md border border-[hsl(var(--divider-subtle))] bg-[hsl(var(--surface))]">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-[hsl(var(--foreground))]">
            {step.name || step.step_id}
          </p>
          <p className="truncate text-xs text-[hsl(var(--muted-foreground))]">
            {line || (
              <span className="font-mono">
                {step.step_id}
                {step.uses ? ` · ${step.uses}` : ""}
              </span>
            )}
          </p>
        </div>
        <Badge variant={statusVariant(step.status)}>{step.status}</Badge>
      </button>
      {open ? (
        <div className="space-y-2 border-t border-[hsl(var(--divider-subtle))] px-3 py-3 text-sm">
          {step.error ? (
            <p className="text-[hsl(var(--destructive))]">{step.error}</p>
          ) : null}
          <div className="grid gap-1 text-[hsl(var(--muted-foreground))] sm:grid-cols-2">
            <span>Started: {step.started_at || "—"}</span>
            <span>Finished: {step.finished_at || "—"}</span>
          </div>
          {step.summary && Object.keys(step.summary).length > 0 ? (
            <details className="text-xs">
              <summary className="cursor-pointer text-[hsl(var(--muted-foreground))]">
                Step details
              </summary>
              <pre className="mt-2 max-h-36 overflow-auto rounded bg-[hsl(var(--surface-elevated))] p-2">
                {JSON.stringify(step.summary, null, 2)}
              </pre>
            </details>
          ) : null}
          {step.artifact_refs && step.artifact_refs.length > 0 ? (
            <div className="space-y-1">
              {step.artifact_refs.map((ref, i) => {
                const hash =
                  typeof ref.artifact_hash === "string"
                    ? ref.artifact_hash
                    : undefined;
                return (
                  <div key={i} className="flex flex-wrap items-center gap-2 text-xs">
                    {hash ? (
                      <Button asChild size="sm" variant="link">
                        <Link to="/artifacts/$hash" params={{ hash }}>
                          Open artifact
                        </Link>
                      </Button>
                    ) : (
                      <code className="break-all text-[hsl(var(--muted-foreground))]">
                        {JSON.stringify(ref)}
                      </code>
                    )}
                  </div>
                );
              })}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function RunTraceView({
  trace,
  artifactHash,
  attestCompleted,
  pipelineId,
}: {
  trace: PipelineRunTrace;
  artifactHash?: string;
  attestCompleted?: boolean;
  pipelineId?: string | null;
}) {
  const steps = useMemo(
    () => collapseApproveTraceSteps(trace.steps || []),
    [trace.steps],
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-[hsl(var(--muted-foreground))]">Pipeline</span>
        <code className="text-xs">{trace.pipeline_id}</code>
        {trace.pipeline_version ? (
          <Badge variant="outline">v{trace.pipeline_version}</Badge>
        ) : null}
        <Badge variant={statusVariant(trace.final_status)}>
          {trace.final_status}
        </Badge>
        {attestCompleted ? (
          <Badge variant="success">attest completed</Badge>
        ) : null}
        {pipelineId || trace.pipeline_id ? (
          <Button asChild size="sm" variant="secondary">
            <Link
              to="/workshop"
              search={{
                id: pipelineId || trace.pipeline_id,
                shelf: undefined,
              }}
            >
              Open on board
            </Link>
          </Button>
        ) : null}
      </div>
      <div className="space-y-2">
        {steps.map((step, i) => (
          <StepRow key={`${step.step_id}-${step.status}-${i}`} step={step} />
        ))}
      </div>
      {artifactHash ? (
        <Button asChild variant="secondary" size="sm">
          <Link to="/artifacts/$hash" params={{ hash: artifactHash }}>
            Open result artifact
          </Link>
        </Button>
      ) : null}
    </div>
  );
}

/** Extract run_trace from a job result object when present. */
export function runTraceFromJobResult(
  result: unknown,
): PipelineRunTrace | null {
  if (!result || typeof result !== "object") return null;
  const r = result as Record<string, unknown>;
  const trace = r.run_trace;
  if (!trace || typeof trace !== "object") return null;
  const t = trace as Record<string, unknown>;
  if (!Array.isArray(t.steps) || typeof t.pipeline_id !== "string") return null;
  return trace as PipelineRunTrace;
}
