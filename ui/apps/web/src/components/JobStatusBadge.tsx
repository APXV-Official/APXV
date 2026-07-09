import type { Job } from "@apxv/api-client";
import { Badge } from "@apxv/ui";

export function JobStatusBadge({ status }: { status?: Job["status"] | string }) {
  const variant =
    status === "completed"
      ? "success"
      : status === "failed"
        ? "destructive"
        : status === "running"
          ? "default"
          : "secondary";

  return (
    <Badge variant={variant} className="capitalize">
      {status ?? "unknown"}
    </Badge>
  );
}