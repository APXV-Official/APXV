import { getAgent, listAgents, type AgentInfo } from "@apxv/api-client";
import {
  ActionGroup,
  Badge,
  Button,
  DataSurface,
  Input,
  Label,
  PageToolbar,
  SectionHeader,
} from "@apxv/ui";
import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { PageShell } from "../components/PageShell";
import { QueryState } from "../components/QueryState";
import {
  SelectableListBadge,
  SelectableListItem,
} from "../components/SelectableListItem";
import { useDebouncedValue } from "../hooks/use-debounced-value";

function agentKindLabel(agent: AgentInfo): string {
  if (agent.kind === "core") return "core";
  return agent.agent_type || "pack";
}

export function AgentsPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search);

  const agentsQuery = useQuery({
    queryKey: ["agents"],
    queryFn: () => listAgents({ limit: 200 }),
  });

  const agents = agentsQuery.data?.items ?? [];
  const filtered = useMemo(() => {
    if (!debouncedSearch.trim()) return agents;
    const q = debouncedSearch.toLowerCase();
    return agents.filter(
      (agent) =>
        agent.id.toLowerCase().includes(q) ||
        agent.name.toLowerCase().includes(q) ||
        agent.packs.some((p) => p.toLowerCase().includes(q)),
    );
  }, [agents, debouncedSearch]);

  const activeId = selectedId ?? filtered[0]?.id ?? null;

  const detailQuery = useQuery({
    queryKey: ["agents", activeId],
    queryFn: () => getAgent(activeId!),
    enabled: Boolean(activeId),
  });

  const activeAgent = detailQuery.data ?? filtered.find((a) => a.id === activeId);

  return (
    <PageShell wide className="space-y-10">
      <PageToolbar>
        <div className="space-y-1.5">
          <Label htmlFor="agent-search">Search agents</Label>
          <Input
            id="agent-search"
            placeholder="ID, name, or pack…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-64"
          />
        </div>
        <ActionGroup>
          <Button variant="link" size="sm" asChild>
            <Link to="/packs">Pack studio</Link>
          </Button>
          <Button variant="link" size="sm" onClick={() => agentsQuery.refetch()}>
            Refresh
          </Button>
        </ActionGroup>
      </PageToolbar>

      <div className="grid min-w-0 gap-8 xl:grid-cols-12 xl:gap-10">
        <section className="min-w-0 space-y-4 xl:col-span-5">
          <SectionHeader
            title="Registry"
            action={
              <span className="text-sm text-[hsl(var(--muted-foreground))]">
                {filtered.length}
              </span>
            }
          />
          <DataSurface>
            <QueryState
              isLoading={agentsQuery.isLoading}
              isError={agentsQuery.isError}
              error={agentsQuery.error}
              isEmpty={!agentsQuery.isLoading && filtered.length === 0}
              emptyTitle="No agents found"
              emptyDescription="Install or activate an agent pack to populate the registry."
            >
              <div className="divide-y divide-[hsl(var(--divider-subtle))]">
                {filtered.map((agent) => (
                  <SelectableListItem
                    key={agent.id}
                    selected={activeId === agent.id}
                    onClick={() => setSelectedId(agent.id)}
                    title={agent.name}
                    subtitle={agent.id}
                    badge={
                      <SelectableListBadge>{agentKindLabel(agent)}</SelectableListBadge>
                    }
                    meta={
                      agent.packs.length > 0
                        ? `${agent.packs.length} pack(s)`
                        : "core only"
                    }
                  />
                ))}
              </div>
            </QueryState>
          </DataSurface>
        </section>

        <section className="min-w-0 space-y-5 border-t border-[hsl(var(--divider))] pt-6 xl:col-span-7 xl:border-l xl:border-t-0 xl:pl-10 xl:pt-0">
          <SectionHeader title={activeAgent?.name ?? "Agent detail"} />

          {activeAgent ? (
            <>
              <p className="font-mono text-sm text-[hsl(var(--muted-foreground))]">
                {activeAgent.id}
              </p>
              {activeAgent.description && (
                <p className="text-sm leading-relaxed text-[hsl(var(--muted-foreground))]">
                  {activeAgent.description}
                </p>
              )}

              <dl className="grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-[hsl(var(--caption))]">Kind</dt>
                  <dd className="mt-0.5 font-medium">{activeAgent.kind}</dd>
                </div>
                <div>
                  <dt className="text-[hsl(var(--caption))]">Type</dt>
                  <dd className="mt-0.5 font-medium">{activeAgent.agent_type}</dd>
                </div>
                {activeAgent.module && (
                  <div className="sm:col-span-2">
                    <dt className="text-[hsl(var(--caption))]">Module</dt>
                    <dd className="mt-0.5 font-mono text-xs">{activeAgent.module}</dd>
                  </div>
                )}
              </dl>

              {activeAgent.packs.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">Owning packs</p>
                  <div className="flex flex-wrap gap-2">
                    {activeAgent.packs.map((packId) => (
                      <Button key={packId} variant="link" size="sm" asChild className="h-auto p-0">
                        <Link to="/packs">{packId}</Link>
                      </Button>
                    ))}
                  </div>
                </div>
              )}

              {activeAgent.capabilities.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">Capabilities</p>
                  <div className="flex flex-wrap gap-2">
                    {activeAgent.capabilities.map((cap) => (
                      <Badge key={cap} variant="secondary" className="font-normal">
                        {cap}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <ActionGroup>
                <Button variant="link" asChild>
                  <Link to="/pipeline">Run in pipeline</Link>
                </Button>
                <Button variant="link" asChild>
                  <Link to="/governance" search={{ tab: "specs", proposal: undefined }}>
                    Governance specs
                  </Link>
                </Button>
              </ActionGroup>
            </>
          ) : (
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              Select an agent to inspect capabilities and pack membership.
            </p>
          )}
        </section>
      </div>
    </PageShell>
  );
}