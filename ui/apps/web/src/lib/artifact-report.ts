import type { ArtifactSummary } from "@apxv/api-client";

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function formatRedactionRow(entry: Record<string, unknown>, index: number): string {
  const pattern = entry.pattern ?? entry.pattern_id ?? entry.type ?? "—";
  const field = entry.field ?? entry.path ?? entry.location ?? "—";
  const count = entry.count ?? entry.matches ?? 1;
  return `| ${index + 1} | ${String(pattern)} | ${String(field)} | ${String(count)} |`;
}

export function buildArtifactReportMarkdown(
  hash: string,
  artifactData: Record<string, unknown>,
  summary?: ArtifactSummary | null,
): string {
  const root = asRecord(artifactData.artifact ?? artifactData);
  const proposed = asRecord(root.proposed_artifact);
  const output = asRecord(proposed.output);
  const governance = asRecord(root.governance_decision);
  const redactions = Array.isArray(output.redactions)
    ? output.redactions
    : Array.isArray(output.redactions_applied)
      ? output.redactions_applied
      : [];

  const lines: string[] = [
    "# APXV Artifact Report",
    "",
    `**Artifact hash:** \`${hash}\``,
    `**Generated:** ${new Date().toISOString()}`,
    "",
    "## Summary",
    "",
    "| Field | Value |",
    "| --- | --- |",
    `| Final status | ${summary?.final_status ?? root.final_status ?? "—"} |`,
    `| Attestation ID | ${summary?.attestation_id ?? root.attestation_id ?? "—"} |`,
    `| Total redactions | ${summary?.total_redactions ?? output.total_redactions ?? redactions.length} |`,
    `| Governance decision | ${summary?.governance_decision ?? governance.decision ?? "—"} |`,
    `| Compliance policy | ${summary?.compliance_policy_id ?? root.compliance_policy_id ?? "—"} |`,
    `| ZK proofs | ${summary?.has_zk ?? Object.keys(root).some((k) => k.startsWith("zk_proof_")) ? "Present" : "None"} |`,
    "",
  ];

  if (redactions.length > 0) {
    lines.push("## Redactions", "", "| # | Pattern | Field | Count |", "| --- | --- | --- | --- |");
    redactions.forEach((item, index) => {
      lines.push(formatRedactionRow(asRecord(item), index));
    });
    lines.push("");
  } else {
    lines.push("## Redactions", "", "_No redaction entries in this artifact._", "");
  }

  const zkKeys = Object.keys(root).filter((k) => k.startsWith("zk_proof_"));
  if (zkKeys.length > 0) {
    lines.push("## Zero-knowledge proofs", "");
    for (const key of zkKeys.sort()) {
      const proof = asRecord(root[key]);
      lines.push(`### ${key}`, "");
      lines.push(`- Circuit: ${proof.circuit_id ?? proof.circuit ?? "—"}`);
      lines.push(`- Verified: ${proof.verified ?? proof.valid ?? "—"}`);
      lines.push("");
    }
  }

  lines.push("## Raw metadata", "", "```json");
  lines.push(JSON.stringify({ summary, artifact: root }, null, 2));
  lines.push("```", "");

  return lines.join("\n");
}