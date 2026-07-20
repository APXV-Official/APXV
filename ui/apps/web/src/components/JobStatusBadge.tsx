import type { Job } from "@apxv/api-client";
import { Badge } from "@apxv/ui";
import { displayJobOutcome } from "../lib/workshop-pipeline";

export function JobStatusBadge({
  status,
  pipelineFinal,
}: {
  status?: Job["status"] | string;
  /** Composition result final_status when present */
  pipelineFinal?: string | null;
}) {
  const outcome = displayJobOutcome(status, pipelineFinal);
  return (
    <Badge variant={outcome.tone} className="capitalize">
      {outcome.label}
    </Badge>
  );
}
