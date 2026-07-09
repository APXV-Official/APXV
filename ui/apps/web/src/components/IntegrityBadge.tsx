import { getSystemHealth } from "@apxv/api-client";
import { StatusDot } from "@apxv/ui";
import { useQuery } from "@tanstack/react-query";

function integrityTone(
  healthy: boolean | undefined,
  reachable: boolean,
): "success" | "warning" | "destructive" | "muted" {
  if (!reachable) return "destructive";
  if (healthy === true) return "success";
  if (healthy === false) return "warning";
  return "muted";
}

export function IntegrityBadge() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: () => getSystemHealth(),
    refetchInterval: 15_000,
  });

  const reachable = !healthQuery.isError;
  const integrity = healthQuery.data?.integrity;
  const healthy = integrity?.healthy;
  const sovereignOk = integrity?.sovereign_ok ?? integrity?.sovereign_status === "pending";

  let label = "Checking integrity…";
  if (healthQuery.isError) {
    label = "Runtime unreachable";
  } else if (!healthQuery.isLoading) {
    if (healthy) {
      label = healthQuery.data?.sovereign_setup
        ? "Sovereign integrity verified"
        : "Integrity verified";
    } else if (healthy === false) {
      label = sovereignOk === false ? "Sovereign setup required" : "Integrity issues";
    } else {
      label = "Unknown";
    }
  }

  return (
    <div
      className="flex items-center gap-2.5 px-2 py-2 text-xs text-[hsl(var(--caption))]"
      title="Store, audit chains, and sovereign key provenance"
    >
      <StatusDot tone={integrityTone(healthy && sovereignOk !== false, reachable)} />
      <span className="truncate leading-snug">{label}</span>
    </div>
  );
}