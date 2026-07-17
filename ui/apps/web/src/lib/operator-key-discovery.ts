import {
  getOperatorKeyHint,
  getSystemHealth,
  type OperatorKeyHint,
} from "@apxv/api-client";
import { formatApiError } from "./api-errors";
import { invokeTauri, isTauri, type OperatorKeyInfo } from "./tauri";

export type DiscoveredOperatorKey = OperatorKeyHint;

export type OperatorKeyDiscoveryResult =
  | { status: "found"; key: DiscoveredOperatorKey }
  | { status: "unreachable"; message: string }
  | { status: "not_found" };

function fromTauri(info: OperatorKeyInfo): DiscoveredOperatorKey {
  return {
    key: info.key,
    file_path: info.file_path,
    file_content: info.file_content,
    key_id: info.key_id,
  };
}

/** Read OPERATOR-KEY-*.txt from desktop filesystem or local API (no auth). */
export async function discoverOperatorKey(): Promise<OperatorKeyDiscoveryResult> {
  if (isTauri()) {
    try {
      const info = await invokeTauri<OperatorKeyInfo>("read_operator_key");
      return { status: "found", key: fromTauri(info) };
    } catch {
      return { status: "not_found" };
    }
  }

  try {
    await getSystemHealth();
  } catch (err) {
    return {
      status: "unreachable",
      message: formatApiError(err),
    };
  }

  try {
    const hint = await getOperatorKeyHint();
    if (hint?.key) {
      return { status: "found", key: hint };
    }
    return { status: "not_found" };
  } catch {
    return { status: "not_found" };
  }
}