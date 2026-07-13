/** Official pack IDs and Pack Studio helpers (v1.3.2 on-ramp). */

export const REFERENCE_PACK_ID = "apxv-pack-reference-redaction";
export const DOCUMENT_PACK_ID = "apxv-pack-document-processing";
export const AI_GOVERNANCE_PACK_ID = "apxv-pack-ai-governance";

export const PACK_TUTORIAL_URL =
  "https://github.com/APXV-Official/APXV/blob/main/docs/BUILD-YOUR-FIRST-PACK.md";

export const PACK_CATALOG_URL =
  "https://github.com/APXV-Official/APXV/blob/main/docs/PACK-CATALOG.md";

export type PackTemplate = "reference" | "minimal";

export function suggestClonePackId(slug: string): string {
  const clean = slug
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  const suffix = Date.now().toString(36).slice(-4);
  if (!clean) return `apxv-pack-custom-${suffix}`;
  return `apxv-pack-${clean}-${suffix}`;
}

export function defaultQuickCloneId(): string {
  return suggestClonePackId("my-redaction");
}