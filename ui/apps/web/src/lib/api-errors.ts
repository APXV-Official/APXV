import { ApiError } from "@apxv/api-client";

export function formatApiError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return "Invalid or expired API key. Re-run onboarding in Settings.";
    }
    if (error.status === 404) {
      return error.message || "Resource not found.";
    }
    return `${error.message} (${error.status})`;
  }
  if (error instanceof Error) return error.message;
  return "An unexpected error occurred.";
}

export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}