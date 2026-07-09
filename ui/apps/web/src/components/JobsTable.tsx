import type { Job } from "@apxv/api-client";
import {
  ActionGroup,
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
}: {
  jobs: Job[];
  selectedId?: string | null;
  onSelect?: (job: Job) => void;
  onRetry?: (job: Job) => void;
  retryingId?: string | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  emptyAction?: ReactNode;
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
      <p className="text-sm text-[hsl(var(--destructive))]">{errorMessage}</p>
    );
  }

  if (jobs.length === 0) {
    return (
      <EmptyState
        icon={<Clock className="h-5 w-5" />}
        title="No jobs yet"
        description="Run a pipeline to queue your first governed job."
        action={emptyAction}
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
          const pack =
            (job.payload as { pack?: string } | undefined)?.pack ?? "—";
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
                <JobStatusBadge status={job.status} />
              </TableCell>
              <TableCell className="text-sm capitalize">{pack}</TableCell>
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