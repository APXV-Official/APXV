import { getSystemHealth } from "@apxv/api-client";
import { ActionGroup, Alert, AlertDescription, AlertTitle, Button } from "@apxv/ui";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { useApp } from "../context/AppContext";
import { formatApiError } from "../lib/api-errors";
import { shellRedirectTarget } from "../lib/onboarding-nav";
import { getFirstRunPath, isTauri } from "../lib/tauri";
import { router } from "../router";

export function ConnectionBanner() {
  const navigate = useNavigate();
  const location = useRouterState({ select: (s) => s.location });
  const { apiKey, resetOnboarding } = useApp();

  async function reconnect() {
    await resetOnboarding();
    router.update({
      context: {
        onboarded: false,
        sovereignReady: router.options.context?.sovereignReady ?? false,
      },
    });
    await router.invalidate();
    const redirect =
      location.pathname !== "/"
        ? shellRedirectTarget(
            location.pathname,
            location.search as Record<string, unknown>,
          )
        : undefined;
    void navigate({ to: getFirstRunPath(), search: { redirect } });
  }

  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: () => getSystemHealth(),
    retry: 1,
    refetchInterval: 30_000,
    enabled: Boolean(apiKey),
  });

  if (!apiKey) {
    return (
      <Alert variant="destructive" className="mb-6">
        <AlertTitle>Not connected</AlertTitle>
        <AlertDescription className="flex flex-wrap items-center gap-x-7 gap-y-3">
          <span>
            Add your operator API key to run pipelines and manage agents.
            {isTauri()
              ? " Desktop can auto-discover OPERATOR-KEY-*.txt on the Connect step."
              : " Paste the key from managed/config/OPERATOR-KEY-*.txt."}
          </span>
          <ActionGroup>
            <Button variant="link" size="sm" onClick={() => void reconnect()}>
              Connect
            </Button>
            <Button variant="link" size="sm" asChild>
              <Link to="/settings">Open Settings</Link>
            </Button>
          </ActionGroup>
        </AlertDescription>
      </Alert>
    );
  }

  if (healthQuery.isError) {
    return (
      <Alert variant="destructive" className="mb-6">
        <AlertTitle>Runtime unavailable</AlertTitle>
        <AlertDescription className="space-y-3">
          <p>{formatApiError(healthQuery.error)}</p>
          <ActionGroup>
            {isTauri() ? (
              <Button variant="link" size="sm" asChild>
                <Link to="/settings">Start server in Settings</Link>
              </Button>
            ) : (
              <span className="text-sm text-[hsl(var(--muted-foreground))]">
                Start the API with{" "}
                <code className="rounded bg-[hsl(var(--overlay-muted))] px-1.5 py-0.5 text-xs">
                  python -m scripts.apxv_serve
                </code>
              </span>
            )}
            <Button
              variant="link"
              size="sm"
              onClick={() => void healthQuery.refetch()}
            >
              Retry health check
            </Button>
          </ActionGroup>
        </AlertDescription>
      </Alert>
    );
  }

  return null;
}