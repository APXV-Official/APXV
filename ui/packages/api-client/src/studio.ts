/** APXV Studio API — create / test / promote agents, packs, and proof profiles. */

import { apiFetch } from "./http";

export interface StudioAgent {
  id: string;
  name?: string;
  description?: string;
  agent_type?: string;
  capabilities?: string[];
  instruction_md?: string;
  knowledge_md?: string;
  promoted?: boolean;
  maturity?: string;
  last_test?: {
    at?: string;
    final_status?: string;
    pipeline_id?: string;
    error?: string | null;
  } | null;
  path?: string;
}

export interface StudioPack {
  id: string;
  name?: string;
  description?: string;
  rules_md?: string;
  workflow_md?: string;
  knowledge_md?: string;
  agents?: string[];
  promoted?: boolean;
  maturity?: string;
  last_test?: {
    at?: string;
    final_status?: string;
    pipeline_id?: string;
    error?: string | null;
  } | null;
  path?: string;
}

export interface ProofPredicate {
  id: string;
  params?: Record<string, unknown>;
  title?: string;
  description?: string;
  requires_zk?: boolean;
  maps_to_circuits?: string[];
}

export interface StudioProof {
  id: string;
  name?: string;
  description?: string;
  intent_md?: string;
  predicates?: ProofPredicate[];
  proof_spec?: Record<string, unknown>;
  claim_english?: string;
  mapped_circuits?: string[];
  circuit_binding?: string;
  fail_closed?: boolean;
  require_attest?: boolean;
  promoted?: boolean;
  maturity?: string;
  last_test?: {
    at?: string;
    final_status?: string;
    ok?: boolean;
    error?: string | null;
    claim?: Record<string, unknown>;
  } | null;
  path?: string;
}

export interface ProofTemplate {
  id: string;
  name?: string;
  description?: string;
  predicates?: ProofPredicate[];
  require_attest?: boolean;
}

export async function listStudioAgents(): Promise<{ agents: StudioAgent[] }> {
  return apiFetch("/api/v2/studio/agents");
}

export async function saveStudioAgent(body: {
  id: string;
  name: string;
  description?: string;
  agent_type?: string;
  instruction_md?: string;
  knowledge_md?: string;
  capabilities?: string[];
}): Promise<{ message: string; agent: StudioAgent }> {
  return apiFetch("/api/v2/studio/agents", { method: "POST", body });
}

export async function getStudioAgent(id: string): Promise<StudioAgent> {
  return apiFetch(`/api/v2/studio/agents/${encodeURIComponent(id)}`);
}

export async function testStudioAgent(
  id: string,
  body?: { input_text?: string },
): Promise<{
  ok: boolean;
  agent_id: string;
  result: Record<string, unknown>;
  last_test: StudioAgent["last_test"];
}> {
  return apiFetch(`/api/v2/studio/agents/${encodeURIComponent(id)}/test`, {
    method: "POST",
    body: body ?? {},
  });
}

export async function promoteStudioAgent(
  id: string,
  body?: { force?: boolean },
): Promise<{ message: string; agent: StudioAgent }> {
  return apiFetch(`/api/v2/studio/agents/${encodeURIComponent(id)}/promote`, {
    method: "POST",
    body: body ?? {},
  });
}

export async function listStudioPacks(): Promise<{ packs: StudioPack[] }> {
  return apiFetch("/api/v2/studio/packs");
}

export async function saveStudioPack(body: {
  id: string;
  name: string;
  description?: string;
  rules_md?: string;
  workflow_md?: string;
  knowledge_md?: string;
  agent_ids?: string[];
}): Promise<{ message: string; pack: StudioPack }> {
  return apiFetch("/api/v2/studio/packs", { method: "POST", body });
}

export async function getStudioPack(id: string): Promise<StudioPack> {
  return apiFetch(`/api/v2/studio/packs/${encodeURIComponent(id)}`);
}

export async function testStudioPack(
  id: string,
  body?: { input_text?: string },
): Promise<{
  ok: boolean;
  pack_id: string;
  result: Record<string, unknown>;
  last_test: StudioPack["last_test"];
}> {
  return apiFetch(`/api/v2/studio/packs/${encodeURIComponent(id)}/test`, {
    method: "POST",
    body: body ?? {},
  });
}

export async function promoteStudioPack(
  id: string,
  body?: { force?: boolean },
): Promise<{ message: string; pack: StudioPack }> {
  return apiFetch(`/api/v2/studio/packs/${encodeURIComponent(id)}/promote`, {
    method: "POST",
    body: body ?? {},
  });
}

export async function getStudioShelf(): Promise<{
  agents: StudioAgent[];
  packs: StudioPack[];
  proofs?: StudioProof[];
}> {
  return apiFetch("/api/v2/studio/shelf");
}

export async function listStudioProofs(): Promise<{ proofs: StudioProof[] }> {
  return apiFetch("/api/v2/studio/proofs");
}

export async function listProofCatalog(): Promise<{ predicates: ProofPredicate[] }> {
  return apiFetch("/api/v2/studio/proofs/catalog");
}

export async function listProofTemplates(): Promise<{ templates: ProofTemplate[] }> {
  return apiFetch("/api/v2/studio/proofs/templates");
}

export async function saveStudioProof(body: {
  id: string;
  name: string;
  description?: string;
  intent_md?: string;
  predicates: Array<string | { id: string; params?: Record<string, unknown> }>;
  circuit_binding?: string;
  fail_closed?: boolean;
  require_attest?: boolean;
}): Promise<{ message: string; proof: StudioProof }> {
  return apiFetch("/api/v2/studio/proofs", { method: "POST", body });
}

export async function saveStudioProofFromTemplate(body: {
  template_id: string;
  proof_id?: string;
  name?: string;
}): Promise<{ message: string; proof: StudioProof }> {
  return apiFetch("/api/v2/studio/proofs/from-template", { method: "POST", body });
}

export async function getStudioProof(id: string): Promise<StudioProof> {
  return apiFetch(`/api/v2/studio/proofs/${encodeURIComponent(id)}`);
}

export async function testStudioProof(
  id: string,
  body?: { input_text?: string },
): Promise<{
  ok: boolean;
  proof_id: string;
  result: Record<string, unknown>;
  proof_claim?: Record<string, unknown>;
  last_test: StudioProof["last_test"];
}> {
  return apiFetch(`/api/v2/studio/proofs/${encodeURIComponent(id)}/test`, {
    method: "POST",
    body: body ?? {},
  });
}

export async function promoteStudioProof(
  id: string,
  body?: { force?: boolean },
): Promise<{ message: string; proof: StudioProof }> {
  return apiFetch(`/api/v2/studio/proofs/${encodeURIComponent(id)}/promote`, {
    method: "POST",
    body: body ?? {},
  });
}

export async function getProofStudioStatus(): Promise<{
  universal_predicate_v1: { keys_available: boolean; circuit: string };
  predicate_count: number;
  template_count: number;
}> {
  return apiFetch("/api/v2/studio/proofs/status");
}

export async function compileProofIntent(body: {
  intent_md: string;
  proof_id?: string;
  name?: string;
  use_llm?: boolean;
}): Promise<{
  source?: string;
  matched_rules?: string[];
  warnings?: string[];
  proof_spec?: Record<string, unknown>;
  predicates?: ProofPredicate[];
}> {
  return apiFetch("/api/v2/studio/proofs/compile-intent", {
    method: "POST",
    body,
  });
}

export async function saveStudioProofFromIntent(body: {
  intent_md: string;
  proof_id?: string;
  name?: string;
  prefer_universal?: boolean;
}): Promise<{ message: string; proof: StudioProof }> {
  return apiFetch("/api/v2/studio/proofs/from-intent", { method: "POST", body });
}

export async function exportProofClaim(body: {
  proof_profile_id?: string;
  claim?: Record<string, unknown>;
  attested?: Record<string, unknown>;
}): Promise<{ bundle: Record<string, unknown> }> {
  return apiFetch("/api/v2/studio/proofs/export-claim", { method: "POST", body });
}
