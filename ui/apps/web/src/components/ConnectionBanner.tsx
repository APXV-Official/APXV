import { getSystemHealth } from "@apxv/api-client";
import { ActionGroup, Alert, AlertDescription, AlertTitle, Button } from "@apxv/ui";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { useCallback, useState } from "react";
import { useApp } from "../context/AppContext";
import { formatApiError } from "../lib/api-errors";
import { shellRedirectTarget } from "../lib/onboarding-nav";
import { getFirstRunPath, isTauri } from "../lib/tauri";
import { router } from "../router";

const DISMISS_KEY = "apxv.dismissVendorKeyBanner";
const BOOTSTRAP_CMD = "python -m scripts.apxv_bootstrap";

export function ConnectionBanner() {
  const navigate = useNavigate();
  const location = useRouterState({ select: (s) => s.location });
  const { apiKey, resetOnboarding } = useApp();
  const [copied, setCopied] = useState(false);
  const [retryNote, setRetryNote] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState(() => {
    try {
      return sessionStorage.getItem(DISMISS_KEY) === "1";
    } catch {
      return false;
    }
  });

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

  const copyBootstrap = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(BOOTSTRAP_CMD);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(false);
    }
  }, []);

  const dismiss = useCallback(() => {
    try {
      sessionStorage.setItem(DISMISS_KEY, "1");
    } catch {
      /* ignore */
    }
    setDismissed(true);
  }, []);

  if (!apiKey) {
    return (
      <Alert variant="destructive" className="mb-4">
        <AlertTitle>Not connected</AlertTitle>
        <AlertDescription className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <span>
            Add your operator API key to run pipelines and manage agents.
            {isTauri()
              ? " Desktop can auto-discover OPERATOR-KEY-*.txt on the Connect step."
              : " Paste the key from managed/config/OPERATOR-KEY-*.txt."}
          </span>
          <ActionGroup className="gap-x-4">
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
      <Alert variant="destructive" className="mb-4">
        <AlertTitle>Runtime unavailable</AlertTitle>
        <AlertDescription className="space-y-2">
          <p>{formatApiError(healthQuery.error)}</p>
          <ActionGroup className="gap-x-4">
            {isTauri() ? (
              <Button variant="link" size="sm" asChild>
                <Link to="/settings">Start server in Settings</Link>
              </Button>
            ) : (
              <span className="text-xs text-[hsl(var(--muted-foreground))]">
                Start the API:{" "}
                <code className="rounded bg-[hsl(var(--overlay-muted))] px-1.5 py-0.5 font-mono text-[11px]">
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

  const health = healthQuery.data;
  const integrity = health?.integrity;
  const healthy = integrity?.healthy;
  const sovereignOk =
    integrity?.sovereign_ok ?? integrity?.sovereign_status === "pending";
  const degraded =
    health?.status === "degraded" ||
    (healthy === false && !healthQuery.isLoading);

  if (degraded && apiKey && !dismissed) {
    const issues =
      (integrity?.sovereign_issues as string[] | undefined) ??
      (integrity as { recovery_hints?: string[] } | undefined)?.recovery_hints ??
      [];
    const sovereignIssue =
      sovereignOk === false ||
      integrity?.sovereign_status === "vendor_keys" ||
      issues.some((h) => /sovereign|vendor_vk|bootstrap/i.test(String(h)));

    return (
      <Alert
        variant="warning"
        className="mb-4 border-[hsl(var(--warning)/0.45)] bg-[hsl(var(--warning)/0.08)]"
      >
        <AlertTitle>
          {sovereignIssue
            ? "Proving keys: vendor defaults (safe to operate)"
            : "Runtime degraded (safe to operate)"}
        </AlertTitle>
        <AlertDescription className="space-y-2.5">
          <p className="text-xs leading-relaxed text-[hsl(var(--muted-foreground))]">
            {sovereignIssue
              ? "Store and audit chains are fine. Your Groth16 verification keys still match the shipped vendor set — proofs work, but are not operator-sovereign until you run local bootstrap once."
              : "The runtime reports degraded health. Studio, Workbench, and Runs usually still work — open System for details."}
          </p>
          {issues[0] ? (
            <p className="break-all font-mono text-[10px] text-[hsl(var(--muted-foreground))]">
              {String(issues[0])}
            </p>
          ) : null}
          {sovereignIssue ? (
            <div className="flex flex-wrap items-center gap-2 rounded-md border border-[hsl(var(--divider-subtle))] bg-[hsl(var(--surface))] px-2.5 py-2">
              <code className="min-w-0 flex-1 break-all font-mono text-[11px] text-[hsl(var(--foreground))]">
                {BOOTSTRAP_CMD}
              </code>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                className="shrink-0"
                onClick={() => void copyBootstrap()}
              >
                {copied ? "Copied" : "Copy command"}
              </Button>
            </div>
          ) : null}
          {retryNote ? (
            <p className="text-[11px] text-[hsl(var(--muted-foreground))]">
              {retryNote}
            </p>
          ) : null}
          <ActionGroup className="gap-x-4">
            <Button
              type="button"
              variant="link"
              size="sm"
              onClick={() => {
                void navigate({ to: "/system", search: { tab: "health" } });
              }}
            >
              Open System health
            </Button>
            <Button
              type="button"
              variant="link"
              size="sm"
              onClick={() => {
                void healthQuery.refetch().then((r) => {
                  const still =
                    r.data?.status === "degraded" ||
                    r.data?.integrity?.healthy === false;
                  const stillVendor =
                    r.data?.integrity?.sovereign_status === "vendor_keys" ||
                    r.data?.integrity?.sovereign_ok === false;
                  setRetryNote(
                    stillVendor
                      ? "Still on vendor keys — run the bootstrap command above in your APXV install directory, then Retry."
                      : still
                        ? "Still degraded — check System health for doctor details."
                        : "Health is clear.",
                  );
                  if (!still) {
                    try {
                      sessionStorage.removeItem(DISMISS_KEY);
                    } catch {
                      /* ignore */
                    }
                  }
                });
              }}
            >
              Retry
            </Button>
            <Button type="button" variant="link" size="sm" onClick={dismiss}>
              Dismiss for session
            </Button>
          </ActionGroup>
          {sovereignIssue ? (
            <p className="text-[10px] text-[hsl(var(--muted-foreground))]">
              Run from the apxv-dev (or install) root. Optional:{" "}
              <code className="font-mono">--skip-ollama --skip-voice</code> for
              keys-only. Restart the API after bootstrap.
            </p>
          ) : null}
        </AlertDescription>
      </Alert>
    );
  }

  return null;
}
