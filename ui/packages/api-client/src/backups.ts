import { apiFetch } from "./http";

export interface BackupInfo {
  filename: string;
  path?: string;
  backup_id?: string;
  created_at?: string;
  file_count?: number;
  size_bytes?: number;
  verified?: boolean;
}

export async function listBackups(): Promise<{ backups: BackupInfo[] }> {
  return apiFetch<{ backups: BackupInfo[] }>("/api/v2/backups");
}

export async function createBackup(): Promise<Record<string, unknown>> {
  return apiFetch("/api/v2/backups", { method: "POST", body: {} });
}

export async function restoreBackup(
  filename: string,
  options?: { dry_run?: boolean; no_safety_backup?: boolean },
): Promise<Record<string, unknown>> {
  return apiFetch("/api/v2/backups/restore", {
    method: "POST",
    body: {
      filename,
      dry_run: options?.dry_run ?? false,
      no_safety_backup: options?.no_safety_backup ?? false,
    },
  });
}