/** APXV operator keys are URL-safe tokens (base64url-style). */
const API_KEY_PATTERN = /^[A-Za-z0-9_-]{20,128}$/;

/**
 * Normalize pasted operator key text (file snippet, bullets, whitespace).
 * Returns null if no plausible key token is found.
 */
export function normalizeOperatorApiKey(raw: string): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;

  const fromFile = trimmed.match(/API\s*Key:\s*([A-Za-z0-9_-]+)/i);
  if (fromFile?.[1]) return fromFile[1];

  const deBulleted = trimmed
    .replace(/[•·●∙◦\u2022\u2023\u25E6\u2219]/g, "")
    .replace(/\s+/g, "");

  if (API_KEY_PATTERN.test(deBulleted)) return deBulleted;

  const token = deBulleted.match(/[A-Za-z0-9_-]{20,128}/)?.[0];
  return token && API_KEY_PATTERN.test(token) ? token : null;
}

export function isValidOperatorApiKey(key: string): boolean {
  return API_KEY_PATTERN.test(key);
}

/** Fetch Headers require ISO-8859-1 header values. */
export function isHeaderSafeAscii(value: string): boolean {
  for (let i = 0; i < value.length; i += 1) {
    const code = value.charCodeAt(i);
    if (code > 255) return false;
  }
  return true;
}