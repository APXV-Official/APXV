/** Client helpers for APXV Workshop composition pipelines. */

import type {
  PipelineDocument,
  PipelineEdge,
  PipelineStep,
} from "@apxv/api-client";

export const PIPELINE_API_VERSION = "apxv.pipeline/v0.1";

export const CORE_AGENT_USES = [
  {
    uses: "agent:APXV-AGENT-001",
    label: "APXV-AGENT-001 — Rule-governed redaction",
  },
  {
    uses: "agent:APXV-AGENT-002",
    label: "APXV-AGENT-002 — Workflow orchestration",
  },
  {
    uses: "agent:APXV-AGENT-003",
    label: "APXV-AGENT-003 — Attestation coordination",
  },
  {
    uses: "agent:APXV-AGENT-LLM-001",
    label: "APXV-AGENT-LLM-001 — LLM reasoner",
  },
  {
    uses: "pack:apxv-pack-reference-redaction",
    label: "Pack — reference redaction",
  },
  {
    uses: "pack:apxv-pack-document-processing",
    label: "Pack — document processing",
  },
  {
    uses: "pack:apxv-pack-ai-governance",
    label: "Pack — AI governance",
  },
  { uses: "apxv:attest", label: "apxv:attest — end-of-pipeline attest step" },
];

export const SAMPLE_PIPELINE_INPUT =
  "Contact John at john.doe@example.com or call (555) 123-4567. SSN: 123-45-6789. Card: 4111 1111 1111 1111.";

export function emptyPipeline(partial?: Partial<PipelineDocument>): PipelineDocument {
  const slug = partial?.id ?? `apxv-pipeline-custom-${Date.now().toString(36).slice(-6)}`;
  return {
    apiVersion: PIPELINE_API_VERSION,
    kind: "Pipeline",
    id: slug,
    name: partial?.name ?? "New composition",
    version: partial?.version ?? "0.1.0",
    description: partial?.description ?? "Operator-authored composition pipeline",
    defaults: {
      attest: false,
      on_step_failure: "stop",
      ...(partial?.defaults ?? {}),
    },
    steps:
      partial?.steps ??
      ([
        {
          id: "redact",
          name: "Rule-governed redaction",
          uses: "agent:APXV-AGENT-001",
        },
      ] as PipelineStep[]),
  };
}

export function newStepId(existing: PipelineStep[]): string {
  let n = existing.length + 1;
  const ids = new Set(existing.map((s) => s.id));
  while (ids.has(`step-${n}`)) n += 1;
  return `step-${n}`;
}

export function defaultStep(existing: PipelineStep[]): PipelineStep {
  const id = newStepId(existing);
  return {
    id,
    name: `Step ${existing.length + 1}`,
    uses: "agent:APXV-AGENT-001",
    enabled: true,
  };
}

export type BlockKind = "agent" | "pack" | "control";

export interface PaletteBlock {
  kind: BlockKind;
  uses: string;
  title: string;
  subtitle: string;
  accent: string;
}

export function paletteFromCatalog(
  agents: Array<{ id: string; name?: string; agent_type?: string; description?: string }>,
  packs: Array<{ id: string; name?: string; description?: string }>,
): PaletteBlock[] {
  const blocks: PaletteBlock[] = [];
  for (const a of agents) {
    blocks.push({
      kind: "agent",
      uses: `agent:${a.id}`,
      title: a.name || a.id,
      subtitle: a.agent_type || "agent",
      accent: "agent",
    });
  }
  for (const p of packs) {
    blocks.push({
      kind: "pack",
      uses: `pack:${p.id}`,
      title: p.name || p.id,
      subtitle: "pack",
      accent: "pack",
    });
  }
  blocks.push(
    {
      kind: "control",
      uses: "apxv:approve",
      title: "Operator approval",
      subtitle: "pause for human",
      accent: "control",
    },
    {
      kind: "control",
      uses: "apxv:attest",
      title: "Attest",
      subtitle: "end-of-run proofs",
      accent: "control",
    },
    {
      kind: "control",
      uses: "apxv:handoff",
      title: "Handoff",
      subtitle: "swarm stage link",
      accent: "control",
    },
    {
      kind: "control",
      uses: "apxv:loop",
      title: "Bounded loop",
      subtitle: "retry / re-enter max N",
      accent: "control",
    },
  );
  return blocks;
}

export function stepFromBlock(
  block: PaletteBlock,
  existing: PipelineStep[],
): PipelineStep {
  const id = newStepId(existing);
  return {
    id,
    name: block.title,
    uses: block.uses,
    enabled: true,
    layout: {
      x: 48 + existing.length * 200,
      y: 120,
    },
  };
}

export function usesKind(uses: string): BlockKind {
  if (uses.startsWith("pack:")) return "pack";
  if (uses.startsWith("apxv:")) return "control";
  return "agent";
}

export type MaturityLabel = "Example" | "Official" | "Core";

/** Honest maturity for shelf / hover (demo packs are Example until Official). */
export function maturityForUses(uses: string): MaturityLabel {
  if (uses.startsWith("agent:APXV-AGENT-OP-")) return "Example";
  if (uses.startsWith("agent:APXV-AGENT-00")) return "Core";
  if (uses.startsWith("agent:APXV-AGENT-LLM-")) return "Core";
  if (uses.startsWith("apxv:")) return "Core";
  if (
    uses.includes("reference-redaction") ||
    uses.includes("document-processing") ||
    uses.includes("ai-governance")
  ) {
    return "Example";
  }
  if (uses.startsWith("pack:")) return "Example";
  return "Example";
}

export function purposeForBlock(block: {
  title: string;
  subtitle: string;
  uses: string;
  kind: BlockKind;
}): string {
  if (block.kind === "control") {
    if (block.uses === "apxv:approve")
      return "Pauses the run until an operator approves or rejects.";
    if (block.uses === "apxv:attest")
      return "Optional end-of-pipeline cryptographic attestation.";
    if (block.uses === "apxv:handoff")
      return "Links this composition to another pipeline (swarm stage).";
    return block.subtitle;
  }
  if (block.kind === "pack") {
    return `Pack kit: ${block.title}. Installs governance + agent bindings for this step.`;
  }
  return block.subtitle || `${block.title} agent building block.`;
}

export type ShelfCategory =
  | "agents"
  | "packs"
  | "proofs"
  | "controls"
  | "library";

export function kindLabel(kind: BlockKind): string {
  if (kind === "pack") return "Pack";
  if (kind === "control") return "Control";
  return "Agent";
}

/** Sync primary pack_profile from attached_packs for runner compatibility. */
export function syncAttachedPacks(step: PipelineStep): PipelineStep {
  const attached = step.attached_packs?.filter(Boolean) ?? [];
  if (!attached.length) return step;
  const primary = attached[0].replace(/^pack:/, "");
  return {
    ...step,
    attached_packs: attached.map((p) =>
      p.startsWith("pack:") ? p : `pack:${p}`,
    ),
    pack_profile: primary,
  };
}

export function pipelineRefBlock(
  pipelineId: string,
  name?: string,
): PaletteBlock {
  return {
    kind: "control",
    uses: "apxv:handoff",
    title: name || pipelineId,
    subtitle: "pipeline link",
    accent: "control",
  };
}

/** Count success outs from a step (for multi-port UI). */
export function successOutCount(
  edges: PipelineEdge[],
  stepId: string,
): number {
  return edges.filter(
    (e) => e.from === stepId && (e.kind || "success") !== "failure",
  ).length;
}

/** Pass A: block Run when the board cannot succeed. */
export function validateCompositionForRun(doc: PipelineDocument): string[] {
  const errors: string[] = [];
  const steps = doc.steps ?? [];
  const edges: PipelineEdge[] = doc.edges ?? [];

  if (steps.length === 0) {
    errors.push("Add at least one building block to the board before running.");
    return errors;
  }

  const enabled = steps.filter((s) => s.enabled !== false);
  if (enabled.length === 0) {
    errors.push("All steps are disabled. Enable at least one step to run.");
  }

  for (const step of steps) {
    if (step.enabled === false) continue;
    if (step.uses === "apxv:handoff") {
      const target = (step.config as { pipeline_id?: string } | undefined)
        ?.pipeline_id;
      if (!target || !String(target).trim()) {
        errors.push(
          `Handoff “${step.name || step.id}” needs a target pipeline — select the block and choose Target pipeline.`,
        );
      }
    }
  }

  if (edges.length > 0) {
    const ids = new Set(steps.map((s) => s.id));
    for (const e of edges) {
      if (!ids.has(e.from) || !ids.has(e.to)) {
        errors.push("A wire points at a missing block. Remove broken wires.");
        break;
      }
    }
    const incoming = new Set(
      edges.filter((e) => (e.kind || "success") !== "failure").map((e) => e.to),
    );
    const roots = steps.filter(
      (s) => s.enabled !== false && !incoming.has(s.id),
    );
    if (roots.length === 0 && enabled.length > 0) {
      errors.push(
        "Every enabled step has an incoming wire (cycle). Leave at least one entry block without an input wire.",
      );
    }
  }
  // No freeform edges: runtime uses document order (linear teaching pipelines).
  // Operators may still wire the board for branching; wires are optional for 1..N steps.

  return errors;
}

/** Collapse pause + approve success into one timeline row for display. */
export function collapseApproveTraceSteps<
  T extends { step_id: string; uses?: string; status: string },
>(steps: T[]): T[] {
  const out: T[] = [];
  for (let i = 0; i < steps.length; i++) {
    const cur = steps[i];
    const next = steps[i + 1];
    if (
      cur.uses === "apxv:approve" &&
      cur.status === "awaiting_approval" &&
      next &&
      next.step_id === cur.step_id &&
      next.uses === "apxv:approve" &&
      next.status === "succeeded"
    ) {
      out.push({ ...next, status: "succeeded" });
      i += 1;
      continue;
    }
    out.push(cur);
  }
  return out;
}

export function displayJobOutcome(
  jobStatus: string | undefined,
  pipelineFinal?: string | null,
): { label: string; tone: "success" | "destructive" | "warning" | "default" | "secondary" } {
  const pf = (pipelineFinal || "").toLowerCase();
  if (jobStatus === "awaiting_approval" || pf === "awaiting_approval") {
    return { label: "Awaiting approval", tone: "warning" };
  }
  if (pf === "failed" || jobStatus === "failed") {
    return { label: "Failed", tone: "destructive" };
  }
  if (pf === "succeeded" || jobStatus === "completed") {
    return { label: pf === "succeeded" ? "Succeeded" : "Completed", tone: "success" };
  }
  if (jobStatus === "running" || jobStatus === "queued") {
    return { label: jobStatus, tone: "default" };
  }
  return { label: jobStatus || "unknown", tone: "secondary" };
}

export function moveStep(
  steps: PipelineStep[],
  index: number,
  direction: -1 | 1,
): PipelineStep[] {
  const next = [...steps];
  const target = index + direction;
  if (target < 0 || target >= next.length) return steps;
  const tmp = next[index];
  next[index] = next[target];
  next[target] = tmp;
  return next;
}

export function downloadText(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
