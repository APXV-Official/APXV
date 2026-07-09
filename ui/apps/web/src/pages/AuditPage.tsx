import { getAuditEntries, listAuditLogs } from "@apxv/api-client";
import {
  ActionGroup,
  Alert,
  AlertDescription,
  Button,
  DataSurface,
  Input,
  Label,
  SectionHeader,
  Select,
  StatusDot,
} from "@apxv/ui";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { PageShell } from "../components/PageShell";
import { QueryState } from "../components/QueryState";
import { SelectableListItem } from "../components/SelectableListItem";
import { formatApiError } from "../lib/api-errors";
import { VirtualizedTable } from "../components/VirtualizedTable";

function formatTime(value?: string) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export function AuditPage() {
  const [selectedLog, setSelectedLog] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [eventFilter, setEventFilter] = useState("");

  const logsQuery = useQuery({
    queryKey: ["audit", "logs"],
    queryFn: () => listAuditLogs(),
  });

  const logs = logsQuery.data?.logs ?? [];
  const activeLog = selectedLog ?? logs[0]?.name ?? null;

  const entriesQuery = useQuery({
    queryKey: ["audit", "entries", activeLog],
    queryFn: () => getAuditEntries(activeLog!, { limit: 200, offset: 0 }),
    enabled: Boolean(activeLog),
  });

  const filteredEntries = useMemo(() => {
    const items = entriesQuery.data?.items ?? [];
    return items.filter((entry) => {
      const q = search.toLowerCase();
      const matchesSearch =
        !q ||
        (entry.event_type ?? "").toLowerCase().includes(q) ||
        JSON.stringify(entry.data ?? {}).toLowerCase().includes(q) ||
        (entry.current_hash ?? "").toLowerCase().includes(q);
      const matchesEvent =
        !eventFilter || entry.event_type === eventFilter;
      return matchesSearch && matchesEvent;
    });
  }, [entriesQuery.data?.items, search, eventFilter]);

  const eventTypes = useMemo(() => {
    const types = new Set<string>();
    for (const entry of entriesQuery.data?.items ?? []) {
      if (entry.event_type) types.add(entry.event_type);
    }
    return Array.from(types).sort();
  }, [entriesQuery.data?.items]);

  return (
    <PageShell wide className="space-y-10">
      {logsQuery.isError && (
        <Alert variant="destructive">
          <AlertDescription>{formatApiError(logsQuery.error)}</AlertDescription>
        </Alert>
      )}

      <div className="grid min-w-0 gap-8 xl:grid-cols-12 xl:gap-10">
        <section className="min-w-0 space-y-4 xl:col-span-4">
          <SectionHeader title="Audit logs" />
          <QueryState
            isLoading={logsQuery.isLoading}
            isEmpty={!logsQuery.isLoading && !logsQuery.isError && logs.length === 0}
            emptyTitle="No audit logs"
            emptyDescription="Audit logs appear after the runtime processes governed actions."
          >
            <DataSurface>
              <div className="divide-y divide-[hsl(var(--divider-subtle))]">
                {logs.map((log) => (
                  <SelectableListItem
                    key={log.name}
                    selected={activeLog === log.name}
                    onClick={() => setSelectedLog(log.name)}
                    title={log.name}
                    meta={`${log.entry_count} entries`}
                    badge={
                      <span className="inline-flex items-center gap-1.5 text-xs text-[hsl(var(--muted-foreground))]">
                        <StatusDot
                          tone={log.chain_valid ? "success" : "destructive"}
                        />
                        {log.chain_valid ? "Valid" : "Broken"}
                      </span>
                    }
                  />
                ))}
              </div>
            </DataSurface>
          </QueryState>
        </section>

        <section className="min-w-0 space-y-4 border-t border-[hsl(var(--divider))] pt-6 xl:col-span-8 xl:border-l xl:border-t-0 xl:pl-10 xl:pt-0">
          <SectionHeader
            title="Audit explorer"
            action={
              entriesQuery.data ? (
                <span className="inline-flex items-center gap-2 text-sm text-[hsl(var(--muted-foreground))]">
                  <StatusDot
                    tone={entriesQuery.data.chain_valid ? "success" : "destructive"}
                  />
                  Chain {entriesQuery.data.chain_valid ? "valid" : "invalid"}
                </span>
              ) : undefined
            }
          />
          {activeLog && (
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              Events in <span className="font-mono">{activeLog}</span>
            </p>
          )}

          <ActionGroup className="items-end">
            <div className="space-y-1.5">
              <Label htmlFor="audit-search">Search entries</Label>
              <Input
                id="audit-search"
                placeholder="Search events, data, hashes…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="max-w-xs"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="audit-event-filter">Event type</Label>
              <Select
                id="audit-event-filter"
                value={eventFilter}
                onChange={(e) => setEventFilter(e.target.value)}
              >
                <option value="">All event types</option>
                {eventTypes.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </Select>
            </div>
            <Button variant="link" size="sm" onClick={() => entriesQuery.refetch()}>
              Refresh
            </Button>
          </ActionGroup>

          <DataSurface>
            <QueryState
              isLoading={entriesQuery.isLoading}
              isError={entriesQuery.isError}
              error={entriesQuery.error}
              isEmpty={
                !entriesQuery.isLoading &&
                !entriesQuery.isError &&
                filteredEntries.length === 0
              }
              emptyTitle="No matching entries"
              emptyDescription="Try a different search or event filter."
            >
              <VirtualizedTable
                rows={filteredEntries}
                rowKey={(entry) =>
                  `${entry.current_hash ?? "row"}-${entry.timestamp ?? ""}-${entry.event_type ?? ""}`
                }
                estimateSize={52}
                maxHeight={520}
                columns={[
                  {
                    id: "time",
                    header: "Time",
                    width: "9rem",
                    className: "text-[hsl(var(--muted-foreground))]",
                    cell: (entry) => formatTime(entry.timestamp),
                  },
                  {
                    id: "event",
                    header: "Event",
                    width: "11rem",
                    className: "font-mono",
                    cell: (entry) => entry.event_type ?? "—",
                  },
                  {
                    id: "hash",
                    header: "Hash",
                    width: "9rem",
                    className: "font-mono",
                    cell: (entry) =>
                      entry.current_hash
                        ? `${entry.current_hash.slice(0, 12)}…`
                        : "—",
                  },
                  {
                    id: "data",
                    header: "Data",
                    width: "minmax(0, 2fr)",
                    className: "text-[hsl(var(--muted-foreground))]",
                    cell: (entry) => JSON.stringify(entry.data ?? {}),
                  },
                ]}
              />
            </QueryState>
          </DataSurface>

          {entriesQuery.data && (
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              Showing {filteredEntries.length} of {entriesQuery.data.total} entries
            </p>
          )}
        </section>
      </div>
    </PageShell>
  );
}