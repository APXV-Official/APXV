import { apiFetch } from "./http";

export interface AuditRepairResult {
  message: string;
  repair: {
    logs: Record<
      string,
      {
        repaired?: boolean;
        chain_valid?: boolean;
        entries?: number;
        backup?: string;
      }
    >;
    all_valid: boolean;
  };
  integrity: Record<string, unknown>;
}

export async function repairAuditLogs(): Promise<AuditRepairResult> {
  return apiFetch<AuditRepairResult>("/api/v2/system/repair-audit", {
    method: "POST",
    body: {},
  });
}