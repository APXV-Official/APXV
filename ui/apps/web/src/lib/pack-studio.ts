/** Official pack IDs and Pack Studio helpers (v1.4 authoring wizard). */

export const REFERENCE_PACK_ID = "apxv-pack-reference-redaction";
export const DOCUMENT_PACK_ID = "apxv-pack-document-processing";
export const AI_GOVERNANCE_PACK_ID = "apxv-pack-ai-governance";

export const PACK_TUTORIAL_URL =
  "https://github.com/APXV-Official/APXV/blob/main/docs/BUILD-YOUR-FIRST-PACK.md";

export const PACK_CATALOG_URL =
  "https://github.com/APXV-Official/APXV/blob/main/docs/PACK-CATALOG.md";

export type PackTemplate = "reference" | "minimal";

export const PACK_ID_PATTERN = /^apxv-pack-[a-z0-9][a-z0-9-]*$/;

export const PIPELINE_COMPOSER_V15_NOTE =
  "Drag-and-drop agent selection and custom step order ship in v1.5. Today: templates, governance edits, activate, and test run.";

export const WIZARD_STEPS = [
  { id: "template", label: "Template" },
  { id: "identity", label: "Name pack" },
  { id: "governance", label: "Governance" },
  { id: "activate", label: "Activate" },
  { id: "test", label: "Test run" },
] as const;

export type WizardStepId = (typeof WIZARD_STEPS)[number]["id"];

export function packIdFromSlug(slug: string): string {
  const clean = slug
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return clean ? `apxv-pack-${clean}` : "";
}

export function validatePackId(packId: string): string | null {
  if (!packId.trim()) return "Pack id is required.";
  if (!PACK_ID_PATTERN.test(packId.trim().toLowerCase())) {
    return "Use apxv-pack-<slug> (lowercase letters, numbers, hyphens only).";
  }
  return null;
}

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

export function packKindFromInfo(pack: { id: string }): string {
  const id = pack.id.toLowerCase();
  if (id.includes("document")) return "document";
  if (id.includes("ai")) return "ai";
  if (id.includes("reference")) return "reference";
  return "custom";
}