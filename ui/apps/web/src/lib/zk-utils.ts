export interface ZkProofNode {
  id: string;
  kind: "governance" | "entity" | "artifact";
  circuit?: string;
  status?: string;
  valid?: boolean;
  publicInputs?: Record<string, unknown>;
  detail?: unknown;
}

export function isZkValid(result: unknown): boolean {
  if (result === true || result === "VALID") return true;
  return false;
}

export function extractArtifactZkNodes(
  data: Record<string, unknown>,
): ZkProofNode[] {
  const artifact = (data.artifact ?? data) as Record<string, unknown>;
  const nodes: ZkProofNode[] = [];

  for (const key of Object.keys(artifact)) {
    if (!key.startsWith("zk_proof_")) continue;
    const proof = artifact[key] as Record<string, unknown> | undefined;
    const circuit = String(proof?.circuit ?? key.replace("zk_proof_", ""));
    nodes.push({
      id: key,
      kind: "artifact",
      circuit,
      status: String(proof?.status ?? "embedded"),
      valid: proof?.verification_result
        ? isZkValid(proof.verification_result)
        : undefined,
      publicInputs:
        (proof?.public_inputs as Record<string, unknown>) ?? undefined,
      detail: proof?.message ? String(proof.message) : undefined,
    });
  }

  const entityProofs = (
    artifact.entity_proofs as { proofs?: Record<string, unknown> } | undefined
  )?.proofs;
  if (entityProofs) {
    for (const [proofKey, bundle] of Object.entries(entityProofs)) {
      const proof = bundle as Record<string, unknown>;
      nodes.push({
        id: proofKey,
        kind: "entity",
        circuit: proofKey.replace(/_/g, "-"),
        status: "entity_proof",
        publicInputs:
          (proof.public_inputs as Record<string, unknown>) ?? undefined,
        detail: proof.proof_hex
          ? `proof ${String(proof.proof_hex).slice(0, 24)}…`
          : undefined,
      });
    }
  }

  return nodes;
}

export function extractReportZkNodes(
  zk: VerificationReportZk | null | undefined,
): ZkProofNode[] {
  if (!zk) return [];
  const nodes: ZkProofNode[] = [];

  for (const [circuit, report] of Object.entries(zk.governance ?? {})) {
    nodes.push({
      id: `gov-${circuit}`,
      kind: "governance",
      circuit,
      status: report.status,
      valid: isZkValid(report.verification_result),
      detail: report.output ?? report.stderr ?? report.error,
    });
  }

  for (const [proofKey, report] of Object.entries(zk.entity ?? {})) {
    nodes.push({
      id: `entity-${proofKey}`,
      kind: "entity",
      circuit: report.circuit ?? proofKey,
      status: report.status,
      valid: isZkValid(report.verification_result),
      detail: report.message ?? report.stderr ?? report.error,
    });
  }

  return nodes;
}

interface VerificationReportZk {
  governance?: Record<
    string,
    {
      status?: string;
      circuit?: string;
      verification_result?: boolean | string;
      message?: string;
      stderr?: string;
      output?: string;
      error?: string;
    }
  >;
  entity?: Record<
    string,
    {
      status?: string;
      circuit?: string;
      verification_result?: boolean | string;
      message?: string;
      stderr?: string;
      error?: string;
    }
  >;
}