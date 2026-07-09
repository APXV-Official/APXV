import { getSystemHealth } from "@apxv/api-client";
import { ActionGroup, Alert, AlertDescription, AlertTitle, Button } from "@apxv/ui";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useApp } from "../context/AppContext";
import { getFirstRunPath } from "../lib/tauri";
import { formatApiError } from "../lib/api-errors";

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
  });

  if (!apiKey) {
    return (
      <Alert variant="destructive" className="mb-6">
        <AlertTitle>Not connected</AlertTitle>
        <AlertDescription className="flex flex-wrap items-center gap-x-7 gap-y-3">
          <span>Add your operator API key to run pipelines and manage agents.</span>
          <ActionGroup>
            <Button variant="link" size="sm" onClick={() => void reconnect()}>
              Connect
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
        <AlertDescription>
          {formatApiError(healthQuery.error)} — start the APXV API server on port 8741,
          then refresh this page.
        </AlertDescription>
      </Alert>
    );
  }

  return null;
}