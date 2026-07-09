import { apiFetch } from "./http";

export interface AuditLogInfo {
  name: string;
  chain_valid: boolean;
  entry_count: number;
  path: string;
}

export interface AuditEntry {
  timestamp?: string;
  event_type?: string;
  data?: Record<string, unknown>;
  previous_hash?: string | null;
  current_hash?: string;
}

export interface AuditEntriesPage {
  log: string;
  chain_valid: boolean;
  items: AuditEntry[];
  total: number;
  limit: number;
  offset: number;
}

export async function listAuditLogs(): Promise<{ logs: AuditLogInfo[] }> {
  return apiFetch<{ logs: AuditLogInfo[] }>("/api/v2/audit/logs");
}

export async function getAuditEntries(
  name: string,
  params?: { limit?: number; offset?: number },
): Promise<AuditEntriesPage> {
  const query = new URLSearchParams();
  if (params?.limit) query.set("limit", String(params.limit));
  if (params?.offset) query.set("offset", String(params.offset));
  const suffix = query.size ? `?${query}` : "";
  return apiFetch<AuditEntriesPage>(
    `/api/v2/audit/logs/${encodeURIComponent(name)}/entries${suffix}`,
  );
}