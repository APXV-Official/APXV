/**
 * Pass A pure-helper contract tests (no vitest).
 * Keep behaviour aligned with src/lib/workshop-pipeline.ts.
 * Run: node scripts/pass-a-helpers.test.mjs
 */

function validateCompositionForRun(doc) {
  const errors = [];
  const steps = doc.steps ?? [];
  const edges = doc.edges ?? [];

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
      const target = step.config?.pipeline_id;
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
  } else if (enabled.length > 1) {
    errors.push(
      "Wire your blocks: drag from a block’s right port to another’s left port so the run knows the order.",
    );
  }

  return errors;
}

function collapseApproveTraceSteps(steps) {
  const out = [];
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

function displayJobOutcome(jobStatus, pipelineFinal) {
  const pf = (pipelineFinal || "").toLowerCase();
  if (jobStatus === "awaiting_approval" || pf === "awaiting_approval") {
    return { label: "Awaiting approval", tone: "warning" };
  }
  if (pf === "failed" || jobStatus === "failed") {
    return { label: "Failed", tone: "destructive" };
  }
  if (pf === "succeeded" || jobStatus === "completed") {
    return {
      label: pf === "succeeded" ? "Succeeded" : "Completed",
      tone: "success",
    };
  }
  if (jobStatus === "running" || jobStatus === "queued") {
    return { label: jobStatus, tone: "default" };
  }
  return { label: jobStatus || "unknown", tone: "secondary" };
}

let failed = 0;
function assert(cond, msg) {
  if (!cond) {
    failed += 1;
    console.error("FAIL:", msg);
  } else {
    console.log("ok:", msg);
  }
}

// validateCompositionForRun
assert(
  validateCompositionForRun({ steps: [] }).length === 1,
  "empty board blocked",
);
assert(
  validateCompositionForRun({
    steps: [
      { id: "a", uses: "agent:x", enabled: false },
      { id: "b", uses: "agent:y", enabled: false },
    ],
  }).some((e) => e.includes("disabled")),
  "all disabled blocked",
);
assert(
  validateCompositionForRun({
    steps: [
      { id: "a", uses: "agent:x" },
      { id: "b", uses: "agent:y" },
    ],
    edges: [],
  }).some((e) => e.includes("Wire")),
  "multi-step without wires blocked",
);
assert(
  validateCompositionForRun({
    steps: [
      { id: "a", uses: "agent:x" },
      { id: "b", uses: "agent:y" },
    ],
    edges: [{ from: "a", to: "b", kind: "success" }],
  }).length === 0,
  "wired two-step ok",
);
assert(
  validateCompositionForRun({
    steps: [{ id: "h", name: "Handoff", uses: "apxv:handoff", config: {} }],
  }).some((e) => e.includes("Target pipeline")),
  "handoff without target blocked",
);
assert(
  validateCompositionForRun({
    steps: [
      {
        id: "h",
        name: "Handoff",
        uses: "apxv:handoff",
        config: { pipeline_id: "child" },
      },
    ],
  }).length === 0,
  "handoff with target ok",
);
assert(
  validateCompositionForRun({
    steps: [
      { id: "a", uses: "agent:x" },
      { id: "b", uses: "agent:y" },
    ],
    edges: [
      { from: "a", to: "b" },
      { from: "b", to: "a" },
    ],
  }).some((e) => e.includes("cycle")),
  "cycle blocked",
);

// collapseApproveTraceSteps
const collapsed = collapseApproveTraceSteps([
  {
    step_id: "approve",
    uses: "apxv:approve",
    status: "awaiting_approval",
  },
  { step_id: "approve", uses: "apxv:approve", status: "succeeded" },
  { step_id: "next", uses: "agent:x", status: "succeeded" },
]);
assert(collapsed.length === 2, "approve pause+success collapse to one");
assert(collapsed[0].status === "succeeded", "collapsed approve is succeeded");

// displayJobOutcome honesty
assert(
  displayJobOutcome("completed", "failed").label === "Failed",
  "queue completed + pipeline failed → Failed",
);
assert(
  displayJobOutcome("completed", "succeeded").label === "Succeeded",
  "queue completed + pipeline succeeded → Succeeded",
);
assert(
  displayJobOutcome("awaiting_approval", null).label === "Awaiting approval",
  "HITL awaiting",
);
assert(
  displayJobOutcome("completed", null).label === "Completed",
  "pack job completed without final_status",
);

// maturity labels (U4)
function maturityForUses(uses) {
  if (uses.startsWith("agent:APXV-AGENT-")) return "Core";
  if (uses.startsWith("apxv:")) return "Core";
  return "Example";
}
assert(maturityForUses("agent:APXV-AGENT-001") === "Core", "core agent maturity");
assert(maturityForUses("apxv:approve") === "Core", "control maturity");
assert(maturityForUses("pack:apxv-pack-reference-redaction") === "Example", "demo pack Example");

// multi-port cap idea: 2 success outs max
function successOutCount(edges, stepId) {
  return edges.filter(
    (e) => e.from === stepId && (e.kind || "success") !== "failure",
  ).length;
}
assert(
  successOutCount(
    [
      { from: "a", to: "b", kind: "success" },
      { from: "a", to: "c", kind: "success" },
    ],
    "a",
  ) === 2,
  "two success outs counted",
);

if (failed) {
  console.error(`\n${failed} assertion(s) failed`);
  process.exit(1);
}
console.log("\nPass A helper contract: all ok");
