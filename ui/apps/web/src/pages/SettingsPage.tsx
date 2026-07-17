import {
  createApiKey,
  getCapabilities,
  getOllamaStatus,
  getSystemDoctor,
  getVerifierBundle,
  listApiKeys,
  repairIntegrations,
  revokeApiKey,
} from "@apxv/api-client";
import { APXV_UI_VERSION } from "@apxv/types";
import {
  ActionGroup,
  Alert,
  AlertDescription,
  AlertTitle,
  Button,
  DataSurface,
  Input,
  Label,
  SectionHeader,
  StatusDot,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@apxv/ui";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { PageShell } from "../components/PageShell";
import { useApp } from "../context/AppContext";
import { QueryState } from "../components/QueryState";
import { formatApiError } from "../lib/api-errors";
import { downloadJson } from "../lib/download";
import { getDefaultBaseUrl, getFirstRunPath } from "../lib/tauri";
import { router } from "../router";
import {
  ensureApxvServerStarted,
  formatServerStatus,
  invokeTauri,
  isTauri,
  quitApxvDesktop,
  restartApxvServer,
  type ServerStatus,
} from "../lib/tauri";

export function SettingsPage() {
  const navigate = useNavigate();
  const { apiKey, resetOnboarding, sovereignReady } = useApp();
  const [serverStatus, setServerStatus] = useState<ServerStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [newKeyId, setNewKeyId] = useState("");
  const [newKeyDesc, setNewKeyDesc] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [exportBusy, setExportBusy] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [keyError, setKeyError] = useState<string | null>(null);
  const [repairMessage, setRepairMessage] = useState<string | null>(null);
  const [repairError, setRepairError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  const keysQuery = useQuery({
    queryKey: ["keys"],
    queryFn: () => listApiKeys(),
  });

  const capabilitiesQuery = useQuery({
    queryKey: ["capabilities"],
    queryFn: () => getCapabilities(),
  });

  const ollamaQuery = useQuery({
    queryKey: ["integrations", "ollama"],
    queryFn: () => getOllamaStatus(),
    refetchInterval: 30_000,
  });

  const repairIntegrationsMutation = useMutation({
    mutationFn: () => repairIntegrations(),
    onSuccess: (result) => {
      setRepairError(null);
      const ollama = result.ollama?.verified ? "Ollama ready" : "Ollama incomplete";
      const voice = result.voice?.enabled ? "Vosk ready" : "Voice incomplete";
      setRepairMessage(`${ollama}; ${voice}`);
      void ollamaQuery.refetch();
    },
    onError: (err) => {
      setRepairMessage(null);
      setRepairError(formatApiError(err));
    },
  });

  const createKeyMutation = useMutation({
    mutationFn: () =>
      createApiKey({
        id: newKeyId.trim(),
        description: newKeyDesc,
        role: "operator",
      }),
    onSuccess: (data) => {
      setKeyError(null);
      setCreatedKey(data.api_key ?? null);
      setNewKeyId("");
      setNewKeyDesc("");
      void keysQuery.refetch();
    },
    onError: (err) => setKeyError(formatApiError(err)),
  });

  const revokeMutation = useMutation({
    mutationFn: (id: string) => revokeApiKey(id),
    onSuccess: () => {
      setKeyError(null);
      void keysQuery.refetch();
    },
    onError: (err) => setKeyError(formatApiError(err)),
  });

  async function refreshServerStatus() {
    if (!isTauri()) return;
    setBusy(true);
    setServerError(null);
    try {
      const status = await invokeTauri<ServerStatus>("get_apxv_server_status");
      setServerStatus(status);
    } catch (err) {
      setServerStatus(null);
      setServerError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  }

  async function runServerAction(action: () => Promise<unknown>) {
    if (!isTauri()) return;
    setBusy(true);
    setServerError(null);
    try {
      await action();
      const status = await invokeTauri<ServerStatus>("get_apxv_server_status");
      setServerStatus(status);
      if (!status.port_open) {
        setServerError(
          "Server command finished but port :8741 is still free. Check that Python 3 is installed and use Start server again.",
        );
      }
    } catch (err) {
      setServerError(formatApiError(err));
      try {
        const status = await invokeTauri<ServerStatus>("get_apxv_server_status");
        setServerStatus(status);
      } catch {
        setServerStatus(null);
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleExportVerifierBundle() {
    setExportBusy(true);
    setExportError(null);
    try {
      const [bundle, doctor, capabilities] = await Promise.all([
        getVerifierBundle(),
        getSystemDoctor(false),
        getCapabilities(),
      ]);
      downloadJson(
        `apxv-verifier-bundle-${new Date().toISOString().slice(0, 10)}.json`,
        {
          exported_by: "apxv-operator-console",
          verifier_bundle: bundle,
          doctor_snapshot: doctor,
          capabilities_snapshot: capabilities,
        },
      );
    } catch (err) {
      setExportError(formatApiError(err));
    } finally {
      setExportBusy(false);
    }
  }

  async function handleReset() {
    await resetOnboarding();
    router.update({ context: { onboarded: false, sovereignReady } });
    await router.invalidate();
    void navigate({ to: getFirstRunPath(), search: { redirect: undefined } });
  }

  useEffect(() => {
    if (isTauri()) void refreshServerStatus();
  }, []);

  const keys = keysQuery.data?.keys ?? [];
  const endpointLabel = getDefaultBaseUrl() || "Local runtime (port 8741)";

  return (
    <PageShell className="mx-auto max-w-3xl space-y-10">
      <section className="space-y-6">
        <SectionHeader title="Connection" />
        <div className="divide-y divide-[hsl(var(--divider-subtle))] text-sm">
          <div className="flex items-center justify-between py-3">
            <span className="text-[hsl(var(--muted-foreground))]">API key</span>
            <span className="inline-flex items-center gap-2">
              <StatusDot tone={apiKey ? "success" : "destructive"} />
              {apiKey ? "Configured" : "Missing"}
            </span>
          </div>
          <div className="flex items-center justify-between py-3">
            <span className="text-[hsl(var(--muted-foreground))]">Endpoint</span>
            <span>{endpointLabel}</span>
          </div>
        </div>
        <ActionGroup>
          <Button variant="link" size="sm" onClick={() => void handleReset()}>
            Re-run onboarding
          </Button>
        </ActionGroup>
      </section>

      <section className="space-y-6 border-t border-[hsl(var(--divider))] pt-8">
        <SectionHeader title="API keys" />
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Manage operator keys — secrets are shown once on create.
        </p>
        {keyError && (
          <Alert variant="destructive">
            <AlertDescription>{keyError}</AlertDescription>
          </Alert>
        )}
        <QueryState
          isLoading={keysQuery.isLoading}
          isError={keysQuery.isError}
          error={keysQuery.error}
          isEmpty={false}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="key-id">Key ID</Label>
              <Input
                id="key-id"
                value={newKeyId}
                onChange={(e) => setNewKeyId(e.target.value)}
                placeholder="e.g. operator-2"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="key-desc">Description</Label>
              <Input
                id="key-desc"
                value={newKeyDesc}
                onChange={(e) => setNewKeyDesc(e.target.value)}
                placeholder="Optional"
              />
            </div>
          </div>
          <ActionGroup>
            <Button
              size="sm"
              disabled={!newKeyId.trim() || createKeyMutation.isPending}
              onClick={() => createKeyMutation.mutate()}
            >
              Create key
            </Button>
          </ActionGroup>
          {createdKey && (
            <div className="rounded-lg bg-[hsl(var(--warning))]/10 px-4 py-3">
              <p className="mb-1 text-sm font-medium">Save this key now</p>
              <code className="break-all text-sm">{createdKey}</code>
            </div>
          )}
          {keys.length > 0 && (
            <DataSurface>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {keys.map((k) => (
                    <TableRow key={k.id}>
                      <TableCell className="font-mono">{k.id}</TableCell>
                      <TableCell>{k.role ?? "—"}</TableCell>
                      <TableCell className="text-[hsl(var(--muted-foreground))]">
                        {k.created_at ?? "—"}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="link"
                          size="sm"
                          disabled={revokeMutation.isPending || !k.id}
                          onClick={() => {
                            if (!k.id) return;
                            if (confirm(`Revoke key ${k.id}?`)) {
                              revokeMutation.mutate(k.id);
                            }
                          }}
                        >
                          Revoke
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </DataSurface>
          )}
        </QueryState>
      </section>

      <section className="space-y-6 border-t border-[hsl(var(--divider))] pt-8">
        <SectionHeader title="Integrations" />
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Local Ollama (AI Governance pack) and Vosk voice model. Repair re-runs bootstrap
          integration steps and updates install.json when present.
        </p>
        <div className="divide-y divide-[hsl(var(--divider-subtle))] text-sm">
          <div className="flex items-center justify-between py-3">
            <span className="text-[hsl(var(--muted-foreground))]">Ollama</span>
            <span className="inline-flex items-center gap-2">
              <StatusDot
                tone={
                  ollamaQuery.data?.reachable
                    ? "success"
                    : ollamaQuery.isError
                      ? "destructive"
                      : "muted"
                }
              />
              {ollamaQuery.isLoading
                ? "Checking…"
                : ollamaQuery.data?.reachable
                  ? `Reachable (${ollamaQuery.data.models?.length ?? 0} models)`
                  : "Unreachable"}
            </span>
          </div>
        </div>
        <ActionGroup>
          <Button
            variant="link"
            size="sm"
            disabled={repairIntegrationsMutation.isPending}
            onClick={() => repairIntegrationsMutation.mutate()}
          >
            {repairIntegrationsMutation.isPending
              ? "Repairing integrations…"
              : "Repair integrations"}
          </Button>
        </ActionGroup>
        {repairMessage && (
          <p className="text-sm text-[hsl(var(--muted-foreground))]">{repairMessage}</p>
        )}
        {repairError && (
          <Alert variant="destructive">
            <AlertDescription>{repairError}</AlertDescription>
          </Alert>
        )}
      </section>

      <section className="space-y-6 border-t border-[hsl(var(--divider))] pt-8">
        <SectionHeader title="Verifier bundle" />
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Export ZK verification manifests and a doctor snapshot for offline verification.
        </p>
        <ActionGroup>
          <Button
            variant="link"
            size="sm"
            disabled={exportBusy}
            onClick={() => void handleExportVerifierBundle()}
          >
            {exportBusy ? "Exporting…" : "Download verifier bundle (JSON)"}
          </Button>
        </ActionGroup>
        {exportError && (
          <Alert variant="destructive">
            <AlertTitle>Export failed</AlertTitle>
            <AlertDescription>{exportError}</AlertDescription>
          </Alert>
        )}
        {capabilitiesQuery.data && (
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Capability policy:{" "}
            {String(
              (capabilitiesQuery.data as { trusted?: boolean }).trusted ?? "unknown",
            )}
          </p>
        )}
      </section>

      {isTauri() && (
        <section className="space-y-6 border-t border-[hsl(var(--divider))] pt-8">
          <SectionHeader title="Runtime process" />
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Start and stop the APXV API from the desktop shell.
          </p>
          {serverError && (
            <Alert variant="destructive">
              <AlertDescription>{serverError}</AlertDescription>
            </Alert>
          )}
          {serverStatus && (
            <div className="divide-y divide-[hsl(var(--divider-subtle))] text-sm">
              <div className="flex items-center justify-between py-3">
                <span className="text-[hsl(var(--muted-foreground))]">Port :8741</span>
                <span className="inline-flex items-center gap-2">
                  <StatusDot tone={serverStatus.port_open ? "success" : "muted"} />
                  {serverStatus.port_open ? "Listening" : "Free"}
                </span>
              </div>
              <div className="flex items-center justify-between py-3">
                <span className="text-[hsl(var(--muted-foreground))]">Process</span>
                <span>
                  {serverStatus.running
                    ? `pid ${serverStatus.pid ?? "unknown"}`
                    : "Not running"}
                </span>
              </div>
              <div className="flex items-center justify-between py-3">
                <span className="text-[hsl(var(--muted-foreground))]">Managed by desktop</span>
                <span>{serverStatus.managed ? "Yes" : "External listener"}</span>
              </div>
              <p className="py-3 text-[hsl(var(--muted-foreground))]">
                {formatServerStatus(serverStatus)}
              </p>
            </div>
          )}
          <ActionGroup>
            <Button variant="link" size="sm" disabled={busy} onClick={() => void refreshServerStatus()}>
              Check status
            </Button>
            <Button
              variant="link"
              size="sm"
              disabled={busy}
              onClick={() => void runServerAction(() => ensureApxvServerStarted())}
            >
              Start server
            </Button>
            <Button
              variant="link"
              size="sm"
              disabled={busy}
              onClick={() => void runServerAction(() => invokeTauri("stop_apxv_server"))}
            >
              Stop server
            </Button>
            <Button
              variant="link"
              size="sm"
              disabled={busy}
              onClick={() => void runServerAction(() => restartApxvServer())}
            >
              Restart server
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={busy}
              onClick={() => void quitApxvDesktop()}
            >
              Quit APXV
            </Button>
          </ActionGroup>
        </section>
      )}

      <section className="space-y-4 border-t border-[hsl(var(--divider))] pt-8">
        <SectionHeader title="About APXV™" />
        <p className="text-sm text-[hsl(var(--muted-foreground))]">
          Attested Proof Execution Verified — governed local agents with Groth16
          proofs. Operator console v{APXV_UI_VERSION}.
        </p>
        <p className="text-xs text-[hsl(var(--caption))]">
          APXV™ is a trademark of APXVdev. See NOTICE in the runtime distribution.
        </p>
      </section>
    </PageShell>
  );
}