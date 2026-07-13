import {
  getOperatorKeyHint,
  getSystemHealth,
  type OperatorKeyHint,
} from "@apxv/api-client";
import { invokeTauri, isTauri, type OperatorKeyInfo } from "./tauri";

export type DiscoveredOperatorKey = OperatorKeyHint;

function fromTauri(info: OperatorKeyInfo): DiscoveredOperatorKey {
  return {
    key: info.key,
    file_path: info.file_path,
    file_content: info.file_content,
    key_id: info.key_id,
  };
}

/** Read OPERATOR-KEY-*.txt from desktop filesystem or local API (no auth). */
export async function discoverOperatorKey(): Promise<DiscoveredOperatorKey | null> {
  if (isTauri()) {
    try {
      const info = await invokeTauri<OperatorKeyInfo>("read_operator_key");
      return fromTauri(info);
    } catch {
      return null;
    }
  }

  try {
    await getSystemHealth();
    return await getOperatorKeyHint();
  } catch {
    return null;
  }
}