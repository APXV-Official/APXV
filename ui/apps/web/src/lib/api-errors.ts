import { ApiError } from "@apxv/api-client";

function networkHint(): string {
  return "Start the API on port 8741 (desktop: Settings → Start server; CLI: python -m scripts.apxv_serve).";
}

export function formatApiError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return "Invalid or expired API key. Open Settings → Re-run onboarding, or paste OPERATOR-KEY-*.txt.";
    }
    if (error.status === 403) {
      return `${error.message} — check operator key role and capability policy.`;
    }
    if (error.status === 404) {
      return `${error.message || "Resource not found."} Refresh the list or verify the ID.`;
    }
    if (error.status === 409) {
      return `${error.message} — resolve the conflict, then retry.`;
    }
    if (error.status >= 500) {
      return `${error.message} (${error.status}) — check System health and server logs.`;
    }
    return `${error.message} (${error.status})`;
  }
  if (error instanceof Error) {
    const msg = error.message.toLowerCase();
    if (
      msg.includes("failed to fetch") ||
      msg.includes("load failed") ||
      msg.includes("network")
    ) {
      return `Could not reach the local API. ${networkHint()}`;
    }
    return error.message;
  }
  return "An unexpected error occurred.";
}

export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}