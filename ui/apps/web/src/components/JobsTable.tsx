import type { Job } from "@apxv/api-client";
import {
  ActionGroup,
  Alert,
  AlertDescription,
  Button,
  EmptyState,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@apxv/ui";
import { Link } from "@tanstack/react-router";
import { Clock } from "lucide-react";
import type { ReactNode } from "react";
import { truncateId } from "../lib/format-id";
import { formatRelativeTime } from "../lib/format-time";
import { JobStatusBadge } from "./JobStatusBadge";

export function JobsTable({
  jobs,
  selectedId,
  onSelect,
  onRetry,
  retryingId,
  errorMessage,
  isLoading,
  emptyAction,
  statusFilter,
  onClearFilter,
}: {
  jobs: Job[];
  selectedId?: string | null;
  onSelect?: (job: Job) => void;
  onRetry?: (job: Job) => void;
  retryingId?: string | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  emptyAction?: ReactNode;
  statusFilter?: Job["status"] | "";
  onClearFilter?: () => void;
}) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (errorMessage) {
    return (
      <Alert variant="destructive">
        <AlertDescription>{errorMessage}</AlertDescription>
      </Alert>
    );
  }

  if (jobs.length === 0) {
    const filtered = Boolean(statusFilter);
    const statusLabel = statusFilter
      ? statusFilter.charAt(0).toUpperCase() + statusFilter.slice(1)
      : "";
    return (
      <EmptyState
        icon={<Clock className="h-5 w-5" />}
        title={filtered ? `No ${statusLabel.toLowerCase()} runs` : "No runs yet"}
        description={
          filtered
            ? `No runs match the ${statusLabel.toLowerCase()} filter. Try another status or clear the filter.`
            : "Open Workbench, add building blocks from the shelf, and Run to create your first governed run."
        }
        action={
          filtered && onClearFilter ? (
            <Button size="sm" variant="secondary" onClick={onClearFilter}>
              Clear filter
            </Button>
          ) : (
            emptyAction
          )
        }
      />
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead>Job</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Pack</TableHead>
          <TableHead>Updated</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {jobs.map((job) => {
          const payload = job.payload as
            | { pack?: string; pipeline_id?: string }
            | undefined;
          const result = job.result as
            | { final_status?: string; pipeline_id?: string }
            | undefined;
          const pack =
            payload?.pipeline_id ||
            result?.pipeline_id ||
            payload?.pack ||
            "—";
          const isSelected = selectedId === job.id;
          return (
            <TableRow
              key={job.id}
              className={[
                isSelected ? "bg-[hsl(var(--primary))]/8" : "",
                onSelect && job.id ? "cursor-pointer" : "cursor-default",
              ].join(" ")}
              onClick={() => {
                if (onSelect && job.id) onSelect(job);
              }}
            >
              <TableCell>
                <span
                  className="block font-mono text-xs"
                  title={job.id}
                >
                  {job.id ? truncateId(job.id) : "—"}
                </span>
                <span className="text-xs text-[hsl(var(--muted-foreground))]">
                  {job.type ?? "pipeline"}
                </span>
              </TableCell>
              <TableCell>
                <JobStatusBadge
                  status={job.status}
                  pipelineFinal={result?.final_status}
                />
              </TableCell>
              <TableCell className="max-w-[10rem] truncate text-sm font-mono text-xs" title={pack}>
                {pack}
              </TableCell>
              <TableCell className="text-xs text-[hsl(var(--muted-foreground))]">
                {formatRelativeTime(job.updated_at ?? job.created_at)}
              </TableCell>
              <TableCell className="text-right">
                <div onClick={(e) => e.stopPropagation()}>
                  <ActionGroup className="justify-end">
                    {job.id ? (
                      <Button variant="link" size="sm" asChild>
                        <Link to="/jobs" search={{ id: job.id }}>
                          View
                        </Link>
                      </Button>
                    ) : null}
                    {job.status === "failed" && onRetry && (
                      <Button
                        variant="link"
                        size="sm"
                        disabled={retryingId === job.id}
                        onClick={() => onRetry(job)}
                      >
                        {retryingId === job.id ? "Retrying…" : "Retry"}
                      </Button>
                    )}
                  </ActionGroup>
                </div>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}