import {
  isHeaderSafeAscii,
  isValidOperatorApiKey,
  normalizeOperatorApiKey,
} from "./api-key";

export { normalizeOperatorApiKey, isValidOperatorApiKey } from "./api-key";

export interface ApiConfig {
  baseUrl: string;
  apiKey: string | null;
}

let config: ApiConfig = {
  baseUrl: "",
  apiKey: null,
};

export function configureApi(partial: Partial<ApiConfig>): void {
  config = { ...config, ...partial };
}

export function getApiConfig(): Readonly<ApiConfig> {
  return config;
}

export function withApiDefaults<T extends { baseUrl?: string; apiKey?: string | null }>(
  options: T,
): T & { baseUrl: string; apiKey: string | null } {
  return {
    ...options,
    baseUrl: options.baseUrl ?? config.baseUrl,
    apiKey: options.apiKey !== undefined ? options.apiKey : config.apiKey,
  };
}

/** Auth headers for APXV (Bearer + APXV-API-KEY for Vite proxy compatibility). */
export function authHeaders(apiKey: string | null | undefined): Record<string, string> {
  if (!apiKey) return {};
  const normalized = normalizeOperatorApiKey(apiKey) ?? apiKey.trim();
  if (!isHeaderSafeAscii(normalized) || !isValidOperatorApiKey(normalized)) {
    throw new Error(
      "Invalid API key format. Paste only the key from OPERATOR-KEY-*.txt (no bullet characters).",
    );
  }
  return {
    Authorization: `Bearer ${normalized}`,
    "APXV-API-KEY": normalized,
  };
}

let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

export function notifyUnauthorized(): void {
  unauthorizedHandler?.();
}