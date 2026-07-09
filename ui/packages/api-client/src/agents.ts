import { apiFetch } from "./http";

export interface AgentInfo {
  id: string;
  name: string;
  kind: string;
  agent_type: string;
  module?: string | null;
  description?: string;
  packs: string[];
  capabilities: string[];
  module_files?: string[];
  chain_index?: number;
  declared_module?: string;
  declared_type?: string;
}

export interface AgentListResponse {
  items: AgentInfo[];
  total: number;
  limit: number;
  offset: number;
}

export interface PackAgentChain {
  pack_id: string;
  pack_name?: string;
  agents: AgentInfo[];
  discovered_modules?: Array<{ file: string; stem: string }>;
}

export async function listAgents(params?: {
  limit?: number;
  offset?: number;
}): Promise<AgentListResponse> {
  const limit = params?.limit ?? 100;
  const offset = params?.offset ?? 0;
  return apiFetch<AgentListResponse>(
    `/api/v2/agents?limit=${limit}&offset=${offset}`,
  );
}

export async function getAgent(id: string): Promise<AgentInfo> {
  return apiFetch<AgentInfo>(`/api/v2/agents/${encodeURIComponent(id)}`);
}

export async function getPackAgents(packId: string): Promise<PackAgentChain> {
  return apiFetch<PackAgentChain>(
    `/api/v2/packs/${encodeURIComponent(packId)}/agents`,
  );
}