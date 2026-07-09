import { apiFetch } from "./http";

export interface OperatorKeyHint {
  key: string;
  file_path: string;
  file_content: string;
  key_id: string | null;
}

/** Public setup endpoint — reads OPERATOR-KEY-*.txt from runtime (Docker / local). */
export async function getOperatorKeyHint(): Promise<OperatorKeyHint> {
  return apiFetch<OperatorKeyHint>("/api/v2/system/operator-key-hint");
}