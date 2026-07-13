import { getSystemHealth } from "@apxv/api-client";
import { ActionGroup, Alert, AlertDescription, AlertTitle, Button } from "@apxv/ui";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { useApp } from "../context/AppContext";
import { formatApiError } from "../lib/api-errors";
import { getFirstRunPath, isTauri } from "../lib/tauri";

export function ConnectionBanner() {
  const navigate = useNavigate();
  const { apiKey, resetOnboarding } = useApp();

  async function reconnect() {
    await resetOnboarding();
    void navigate({ to: getFirstRunPath(), search: { redirect: undefined } });
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
            {isTauri() && (
              <Button variant="link" size="sm" asChild>
                <Link to="/settings">Start server in Settings</Link>
              </Button>
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