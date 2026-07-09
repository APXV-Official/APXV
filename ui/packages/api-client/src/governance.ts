import { apiFetch } from "./http";

export type SpecType = "rule" | "workflow" | "knowledge";

export interface GovernanceSpec {
  spec_type?: string;
  content?: string;
  hash?: string;
  id?: string;
  version?: string;
  file_path?: string;
  read_at?: string;
}

export interface GovernanceSpecsResponse {
  specs: Record<SpecType, GovernanceSpec | null>;
  status?: Record<string, unknown>;
}

export interface GovernanceProposal {
  id: string;
  spec_type: SpecType;
  status: "proposed" | "approved" | "rejected" | "applied" | string;
  content_hash?: string;
  proposed_content_relpath?: string;
  proposed_by?: string;
  proposed_at?: string;
  summary?: string;
  current_content_hash?: string | null;
  approved_by?: string;
  approved_at?: string;
  rejected_by?: string;
  rejected_at?: string;
  rejection_reason?: string;
  applied_at?: string;
}

export interface GovernanceProposalDetail {
  proposal: GovernanceProposal;
  content: string;
}

export async function listGovernanceSpecs(): Promise<GovernanceSpecsResponse> {
  return apiFetch<GovernanceSpecsResponse>("/api/v2/governance/specs");
}

export async function listGovernanceProposals(): Promise<{
  proposals: GovernanceProposal[];
}> {
  return apiFetch<{ proposals: GovernanceProposal[] }>(
    "/api/v2/governance/proposals",
  );
}

export async function getGovernanceProposal(
  id: string,
): Promise<GovernanceProposalDetail> {
  return apiFetch<GovernanceProposalDetail>(
    `/api/v2/governance/proposals/${encodeURIComponent(id)}`,
  );
}

export async function createGovernanceProposal(body: {
  spec_type: SpecType;
  content: string;
  summary?: string;
  proposed_by?: string;
}): Promise<{ message: string; proposal: GovernanceProposal }> {
  return apiFetch("/api/v2/governance/proposals", {
    method: "POST",
    body,
  });
}

export async function approveGovernanceProposal(
  id: string,
  approvedBy = "operator-console",
): Promise<Record<string, unknown>> {
  return apiFetch(
    `/api/v2/governance/proposals/${encodeURIComponent(id)}/approve`,
    { method: "POST", body: { approved_by: approvedBy } },
  );
}

export async function rejectGovernanceProposal(
  id: string,
  reason = "",
  rejectedBy = "operator-console",
): Promise<Record<string, unknown>> {
  return apiFetch(
    `/api/v2/governance/proposals/${encodeURIComponent(id)}/reject`,
    { method: "POST", body: { rejected_by: rejectedBy, reason } },
  );
}

export async function applyGovernanceProposal(
  id: string,
): Promise<Record<string, unknown>> {
  return apiFetch(
    `/api/v2/governance/proposals/${encodeURIComponent(id)}/apply`,
    { method: "POST", body: {} },
  );
}