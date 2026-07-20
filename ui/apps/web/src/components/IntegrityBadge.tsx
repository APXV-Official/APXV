import { getSystemHealth } from "@apxv/api-client";
import { StatusDot } from "@apxv/ui";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";

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
  const navigate = useNavigate();
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
      label =
        sovereignOk === false
          ? "Keys: setup recommended"
          : "Integrity check issues";
    } else {
      label = "Unknown";
    }
  }

  return (
    <button
      type="button"
      className="flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-left text-xs text-[hsl(var(--caption))] transition-colors hover:bg-[hsl(var(--overlay-subtle))] hover:text-[hsl(var(--foreground))]"
      title="Open System health — store, audit, and proving-key status"
      onClick={() => {
        void navigate({ to: "/system", search: { tab: "health" } });
      }}
    >
      <StatusDot tone={integrityTone(healthy && sovereignOk !== false, reachable)} />
      <span className="truncate leading-snug">{label}</span>
    </button>
  );
}