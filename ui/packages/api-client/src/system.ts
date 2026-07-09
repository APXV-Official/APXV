import { apiFetch } from "./http";
import type { IntegrityResult } from "./types";

export interface VerifierBundleExport {
  bundle_version: string;
  exported_at: string;
  governance: {
    circuits: string[];
    manifest: Record<string, unknown> | null;
  };
  entity: {
    circuits: string[];
    manifest: Record<string, unknown> | null;
  };
  includes_transcript: boolean;
  ceremony_transcript?: Record<string, unknown>;
}

export async function runIntegrityCheck(): Promise<IntegrityResult> {
  return apiFetch<IntegrityResult>("/api/v2/system/integrity", {
    method: "POST",
    body: {},
  });
}

export async function getVerifierBundle(): Promise<VerifierBundleExport> {
  return apiFetch<VerifierBundleExport>("/api/v2/system/verifier-bundle");
}