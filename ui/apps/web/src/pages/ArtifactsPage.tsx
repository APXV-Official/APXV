import { listArtifacts } from "@apxv/api-client";
import {
  ActionGroup,
  Button,
  DataSurface,
  Input,
  Label,
  PageToolbar,
  SectionHeader,
} from "@apxv/ui";
import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { PageShell } from "../components/PageShell";
import { QueryState } from "../components/QueryState";
import { VirtualizedTable } from "../components/VirtualizedTable";
import { useDebouncedValue } from "../hooks/use-debounced-value";
import { formatRelativeTime } from "../lib/format-time";
import { truncateId } from "../lib/format-id";

export function ArtifactsPage() {
  const [prefix, setPrefix] = useState("");
  const [search, setSearch] = useState("");
  const debouncedPrefix = useDebouncedValue(prefix);

  const artifactsQuery = useQuery({
    queryKey: ["artifacts", debouncedPrefix],
    queryFn: () =>
      listArtifacts({
        limit: 100,
        offset: 0,
        name_prefix: debouncedPrefix || undefined,
      }),
  });

  const items = (artifactsQuery.data?.items ?? []).filter((row) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      row.name.toLowerCase().includes(q) ||
      row.artifact_hash.toLowerCase().includes(q)
    );
  });

  return (
    <PageShell wide className="space-y-10">
      <SectionHeader title="Artifact library" />

      <PageToolbar>
        <ActionGroup className="items-end">
          <div className="space-y-1.5">
            <Label htmlFor="artifact-prefix">Name prefix</Label>
            <Input
              id="artifact-prefix"
              placeholder="Filter prefix…"
              value={prefix}
              onChange={(e) => setPrefix(e.target.value)}
              className="w-44"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="artifact-search">Search</Label>
            <Input
              id="artifact-search"
              placeholder="Name or hash…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-52"
            />
          </div>
        </ActionGroup>
        <ActionGroup>
          <Button variant="link" size="sm" onClick={() => artifactsQuery.refetch()}>
            Refresh
          </Button>
        </ActionGroup>
      </PageToolbar>

      <DataSurface>
        <QueryState
          isLoading={artifactsQuery.isLoading}
          isError={artifactsQuery.isError}
          error={artifactsQuery.error}
          isEmpty={
            !artifactsQuery.isLoading &&
            !artifactsQuery.isError &&
            items.length === 0
          }
          emptyTitle="No artifacts yet"
          emptyDescription="Run a governed pipeline to generate attested outputs."
          emptyAction={
            <Button size="sm" asChild>
              <Link to="/pipeline">Run pipeline</Link>
            </Button>
          }
        >
          <VirtualizedTable
            rows={items}
            rowKey={(row) => row.artifact_hash}
            columns={[
              {
                id: "name",
                header: "Name",
                width: "minmax(0, 2fr)",
                cell: (row) => row.name,
              },
              {
                id: "hash",
                header: "Hash",
                width: "11rem",
                className: "font-mono",
                cell: (row) => truncateId(row.artifact_hash, 12, 8),
              },
              {
                id: "written",
                header: "Written",
                width: "8rem",
                className: "text-[hsl(var(--muted-foreground))]",
                cell: (row) => formatRelativeTime(row.written_at),
              },
              {
                id: "actions",
                header: "",
                width: "6.5rem",
                truncate: false,
                className: "justify-end",
                cell: (row) => (
                  <Button variant="link" size="sm" asChild>
                    <Link
                      to="/artifacts/$hash"
                      params={{ hash: row.artifact_hash }}
                    >
                      Open
                    </Link>
                  </Button>
                ),
              },
            ]}
          />
        </QueryState>
      </DataSurface>

      {artifactsQuery.data && (
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Showing {items.length} of {artifactsQuery.data.total} artifacts
        </p>
      )}
    </PageShell>
  );
}