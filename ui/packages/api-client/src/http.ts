import { authHeaders, notifyUnauthorized, withApiDefaults } from "./configure";
import type { ErrorEnvelope } from "./types";

export class ApiError extends Error {
  status: number;
  code: string;
  details?: Record<string, unknown>;

  constructor(status: number, body: ErrorEnvelope) {
    super(body.message || `API error ${status}`);
    this.status = status;
    this.code = body.error;
    this.details = body.details;
  }
}

export type ApiFetchOptions = {
  baseUrl?: string;
  apiKey?: string | null;
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
};

export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const resolved = withApiDefaults(options);
  const base = resolved.baseUrl.replace(/\/$/, "");
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...options.headers,
  };

  Object.assign(headers, authHeaders(resolved.apiKey));

  let body: string | undefined;
  if (resolved.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(resolved.body);
  }

  const response = await fetch(url, {
    method: resolved.method ?? (body ? "POST" : "GET"),
    headers,
    body,
  });

  const text = await response.text();
  let payload: unknown = {};
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { message: text };
    }
  }

  if (!response.ok) {
    if (response.status === 401) {
      notifyUnauthorized();
    }
    const err = payload as ErrorEnvelope;
    throw new ApiError(response.status, {
      error: err.error ?? "request_failed",
      message: err.message ?? text,
      details: err.details,
    });
  }

  return payload as T;
}