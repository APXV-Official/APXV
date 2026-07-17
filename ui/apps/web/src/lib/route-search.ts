/** Normalize TanStack search values (handles JSON-quoted strings in URLs). */
export function normalizeSearchString(raw: unknown): string | undefined {
  if (raw === undefined || raw === null) return undefined;
  if (typeof raw !== "string") return String(raw);
  const trimmed = raw.trim();
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1) || undefined;
  }
  return trimmed || undefined;
}

export function parseWizardSearch(raw: unknown): "1" | undefined {
  const value = normalizeSearchString(raw);
  return value === "1" ? "1" : undefined;
}