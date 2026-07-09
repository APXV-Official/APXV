/** Mirrors openapi/apxv-api-v2.yaml — replaced by generated types in Phase 1. */

export interface IntegrityResult {
  store_chain_valid?: boolean;
  all_audit_valid?: boolean;
  capability_policy_trusted?: boolean;
  governance_approvals_valid?: boolean;
  healthy?: boolean;
  sovereign_setup?: boolean;
  sovereign_ok?: boolean;
  sovereign_status?: string;
  sovereign_issues?: string[];
  audit_logs?: Record<string, boolean>;
  store_issues?: string[];
  governance_approval_issues?: string[];
}

export interface HealthResponse {
  status: "healthy" | "degraded";
  air_gapped?: boolean;
  sovereign_setup?: boolean;
  integrity?: IntegrityResult;
}

export interface DoctorCheck {
  name: string;
  ok: boolean;
  detail: string;
  required?: string;
}

export interface DoctorResponse {
  healthy: boolean;
  checks: DoctorCheck[];
}

export interface ErrorEnvelope {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}