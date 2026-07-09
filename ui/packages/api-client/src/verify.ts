import { apiFetch } from "./http";

export interface PythonCheck {
  name: string;
  passed: boolean;
  details?: string;
}

export interface PythonVerification {
  attestation_id?: string;
  checks?: PythonCheck[];
  overall_status?: string;
}

export interface ZkCircuitReport {
  status?: string;
  circuit?: string;
  verification_result?: boolean | string;
  message?: string;
  stderr?: string;
  stdout?: string;
  output?: string;
  error?: string;
}

export interface VerificationReport {
  attestation_id?: string;
  overall_valid?: boolean;
  python?: PythonVerification;
  zk?: {
    governance?: Record<string, ZkCircuitReport>;
    entity?: Record<string, ZkCircuitReport>;
  } | null;
}

export async function verifyAttestation(params: {
  artifact_hash?: string;
  attestation?: Record<string, unknown>;
  real_zk?: boolean;
}): Promise<VerificationReport> {
  return apiFetch<VerificationReport>("/api/v2/verify/attestation", {
    method: "POST",
    body: params,
  });
}