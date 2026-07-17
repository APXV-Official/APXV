import {
  createBackup,
  getOllamaStatus,
  getSystemDoctor,
  getSystemStatus,
  listBackups,
  repairAuditLogs,
  restoreBackup,
  runIntegrityCheck,
} from "@apxv/api-client";
import {
  ActionGroup,
  PageToolbar,
  Alert,
  AlertDescription,
  Button,
  Checkbox,
  DataSurface,
  EmptyState,
  SectionHeader,
  Skeleton,
  StatusDot,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@apxv/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { PageShell } from "../components/PageShell";
import { formatApiError } from "../lib/api-errors";
import { formatDoctorCheckSummary } from "../lib/doctor-format";

function formatBytes(n?: number) {
  if (!n) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function formatTime(value?: string) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

const SYSTEM_TABS = ["health", "backups", "integrations"] as const;
type SystemTab = (typeof SYSTEM_TABS)[number];

export function SystemPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { tab: tabParam } = useSearch({ from: "/shell/system" });
  const [activeTab, setActiveTab] = useState<SystemTab>(
    SYSTEM_TABS.includes(tabParam as SystemTab)
      ? (tabParam as SystemTab)
      : "health",
  );

  useEffect(() => {
    if (tabParam && SYSTEM_TABS.includes(tabParam as SystemTab)) {
      setActiveTab(tabParam as SystemTab);
    }
  }, [tabParam]);

  function changeTab(tab: SystemTab) {
    setActiveTab(tab);
    void navigate({ to: "/system", search: { tab } });
  }

  const [checkLlm, setCheckLlm] = useState(false);
  const [selectedBackup, setSelectedBackup] = useState<string | null>(null);
  const [restoreResult, setRestoreResult] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const doctorQuery = useQuery({
    queryKey: ["system", "doctor", checkLlm],
    queryFn: () => getSystemDoctor(checkLlm),
    enabled: activeTab === "health",
  });

  const statusQuery = useQuery({
    queryKey: ["system", "status"],
    queryFn: () => getSystemStatus(),
    enabled: activeTab === "health",
  });

  const backupsQuery = useQuery({
    queryKey: ["backups"],
    queryFn: () => listBackups(),
    enabled: activeTab === "backups",
  });

  const ollamaQuery = useQuery({
    queryKey: ["ollama"],
    queryFn: () => getOllamaStatus(),
    enabled: activeTab === "integrations",
    refetchInterval: 30_000,
  });

  const integrityMutation = useMutation({
    mutationFn: () => runIntegrityCheck(),
    onSuccess: () => {
      setActionMessage({ type: "success", text: "Integrity check completed." });
      void queryClient.invalidateQueries({ queryKey: ["health"] });
      void doctorQuery.refetch();
    },
    onError: (err) =>
      setActionMessage({ type: "error", text: formatApiError(err) }),
  });

  const repairAuditMutation = useMutation({
    mutationFn: () => repairAuditLogs(),
    onSuccess: (data) => {
      setActionMessage({
        type: data.repair.all_valid ? "success" : "error",
        text: data.repair.all_valid
          ? "Audit chains repaired successfully."
          : "Repair completed — some logs may still need attention.",
      });
      void queryClient.invalidateQueries({ queryKey: ["health"] });
      void doctorQuery.refetch();
    },
    onError: (err) =>
      setActionMessage({ type: "error", text: formatApiError(err) }),
  });

  const createBackupMutation = useMutation({
    mutationFn: () => createBackup(),
    onSuccess: () => {
      setActionMessage({ type: "success", text: "Backup created successfully." });
      void backupsQuery.refetch();
    },
    onError: (err) =>
      setActionMessage({ type: "error", text: formatApiError(err) }),
  });

  const dryRunMutation = useMutation({
    mutationFn: (filename: string) =>
      restoreBackup(filename, { dry_run: true }),
    onSuccess: (data) =>
      setRestoreResult(
        `Dry-run OK — would restore ${String(data.file_count ?? "?")} files`,
      ),
    onError: (err) => setRestoreResult(formatApiError(err)),
  });

  const restoreMutation = useMutation({
    mutationFn: (filename: string) => restoreBackup(filename),
    onSuccess: () => {
      setRestoreResult("Backup restored successfully.");
      void backupsQuery.refetch();
      void queryClient.invalidateQueries({ queryKey: ["health"] });
    },
    onError: (err) => setRestoreResult(formatApiError(err)),
  });

  const backups = backupsQuery.data?.backups ?? [];

  return (
    <PageShell wide className="space-y-10">
      {actionMessage && (
        <Alert variant={actionMessage.type === "error" ? "destructive" : "success"}>
          <AlertDescription>{actionMessage.text}</AlertDescription>
        </Alert>
      )}

      <Tabs
        value={activeTab}
        onValueChange={(tab) => changeTab(tab as SystemTab)}
      >
        <TabsList>
          <TabsTrigger value="health">System health</TabsTrigger>
          <TabsTrigger value="backups">Backups</TabsTrigger>
          <TabsTrigger value="integrations">Integrations</TabsTrigger>
        </TabsList>

        <TabsContent value="health" className="space-y-10 pt-6">
          <div className="space-y-6 border-b border-[hsl(var(--divider-subtle))] pb-6">
            <PageToolbar className="border-0 pb-0">
              <span className="inline-flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-[hsl(var(--muted-foreground))]">
                <span className="inline-flex items-center gap-2">
                  <StatusDot
                    tone={doctorQuery.data?.healthy ? "success" : "warning"}
                    pulse={doctorQuery.data?.healthy}
                  />
                  Doctor {doctorQuery.data?.healthy ? "healthy" : "issues"}
                </span>
                {statusQuery.data?.runtime_version && (
                  <span>· v{statusQuery.data.runtime_version}</span>
                )}
              </span>
            </PageToolbar>
            <div className="flex flex-wrap items-center justify-between gap-x-10 gap-y-4">
              <Checkbox
                id="check-llm"
                checked={checkLlm}
                onChange={(e) => setCheckLlm(e.target.checked)}
                label="Include LLM check"
              />
              <ActionGroup>
                <Button variant="link" size="sm" onClick={() => doctorQuery.refetch()}>
                  Re-run doctor
                </Button>
                <Button
                  variant="link"
                  size="sm"
                  disabled={integrityMutation.isPending}
                  onClick={() => integrityMutation.mutate()}
                >
                  Integrity check
                </Button>
                <Button
                  variant="link"
                  size="sm"
                  disabled={repairAuditMutation.isPending}
                  onClick={() => repairAuditMutation.mutate()}
                >
                  {repairAuditMutation.isPending ? "Repairing…" : "Repair audit"}
                </Button>
              </ActionGroup>
            </div>
          </div>

          <section className="space-y-4">
            <SectionHeader title="Doctor checks" />
            <DataSurface>
              {doctorQuery.isError && (
                <Alert variant="destructive" className="mb-4">
                  <AlertDescription className="space-y-3">
                    <p>{formatApiError(doctorQuery.error)}</p>
                    <Button
                      variant="link"
                      size="sm"
                      className="h-auto p-0"
                      onClick={() => void doctorQuery.refetch()}
                    >
                      Retry doctor
                    </Button>
                  </AlertDescription>
                </Alert>
              )}
              {doctorQuery.isLoading ? (
                <div className="space-y-2">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} className="h-9 w-full" />
                  ))}
                </div>
              ) : doctorQuery.isError ? null : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Check</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Detail</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(doctorQuery.data?.checks ?? []).map((check) => (
                      <TableRow key={check.name}>
                        <TableCell className="font-mono">{check.name}</TableCell>
                        <TableCell>
                          <span className="inline-flex items-center gap-2 text-sm">
                            <StatusDot tone={check.ok ? "success" : "destructive"} />
                            {check.ok ? "ok" : "fail"}
                          </span>
                        </TableCell>
                        <TableCell className="text-[hsl(var(--muted-foreground))]">
                          {formatDoctorCheckSummary(
                            check.name ?? "",
                            check.detail,
                            Boolean(check.ok),
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </DataSurface>
          </section>

          {statusQuery.data && (
            <details className="group border-t border-[hsl(var(--divider))] pt-6">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 marker:content-none [&::-webkit-details-marker]:hidden">
                <span className="text-base font-semibold">Runtime details</span>
                <span className="text-sm text-[hsl(var(--muted-foreground))] group-open:hidden">
                  Show JSON
                </span>
              </summary>
              <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
                Version {statusQuery.data.runtime_version ?? "—"} ·{" "}
                {statusQuery.data.deployment ?? "local"}
              </p>
              <pre className="mt-4 max-h-64 overflow-auto rounded-xl bg-[hsl(var(--surface-elevated))] p-4 text-sm">
                {JSON.stringify(statusQuery.data, null, 2)}
              </pre>
            </details>
          )}
        </TabsContent>

        <TabsContent value="backups" className="space-y-10 pt-6">
          <PageToolbar>
            <ActionGroup>
              <Button
                disabled={createBackupMutation.isPending}
                onClick={() => createBackupMutation.mutate()}
              >
                {createBackupMutation.isPending ? "Creating…" : "Create backup"}
              </Button>
              <Button variant="link" size="sm" onClick={() => backupsQuery.refetch()}>
                Refresh
              </Button>
            </ActionGroup>
          </PageToolbar>

          <section className="space-y-4">
            <SectionHeader title="Backup archives" />
            <DataSurface>
              {backups.length === 0 ? (
                <EmptyState
                  title="No backups yet"
                  description="Create a backup to snapshot managed state and keys."
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>File</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Size</TableHead>
                      <TableHead>Files</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {backups.map((b) => (
                      <TableRow key={b.filename}>
                        <TableCell className="font-mono">{b.filename}</TableCell>
                        <TableCell>{formatTime(b.created_at)}</TableCell>
                        <TableCell>{formatBytes(b.size_bytes)}</TableCell>
                        <TableCell>{b.file_count ?? "—"}</TableCell>
                        <TableCell className="text-right">
                          <ActionGroup className="justify-end">
                            <Button
                              variant="link"
                              size="sm"
                              disabled={
                                dryRunMutation.isPending ||
                                restoreMutation.isPending
                              }
                              onClick={() => {
                                setSelectedBackup(b.filename);
                                dryRunMutation.mutate(b.filename);
                              }}
                            >
                              {dryRunMutation.isPending &&
                              selectedBackup === b.filename
                                ? "Dry-running…"
                                : "Dry-run"}
                            </Button>
                            <Button
                              variant="link"
                              size="sm"
                              disabled={restoreMutation.isPending}
                              onClick={() => {
                                if (
                                  confirm(
                                    `Restore ${b.filename}? A safety backup will be created first.`,
                                  )
                                ) {
                                  setSelectedBackup(b.filename);
                                  restoreMutation.mutate(b.filename);
                                }
                              }}
                            >
                              Restore
                            </Button>
                          </ActionGroup>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </DataSurface>
            {restoreResult && selectedBackup && (
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                {selectedBackup}: {restoreResult}
              </p>
            )}
          </section>
        </TabsContent>

        <TabsContent value="integrations" className="space-y-10 pt-6">
          <section className="space-y-4">
            <SectionHeader
              title="Ollama"
              action={
                <Button variant="link" size="sm" onClick={() => ollamaQuery.refetch()}>
                  Refresh
                </Button>
              }
            />
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              Local LLM integration for AI governance pack
            </p>
            <span className="inline-flex items-center gap-2 text-sm">
              <StatusDot tone={ollamaQuery.data?.reachable ? "success" : "warning"} />
              {ollamaQuery.data?.reachable ? "Reachable" : "Unreachable"}
            </span>
            {(ollamaQuery.data?.models ?? []).length === 0 ? (
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                No models reported. Ensure Ollama is running on localhost.
              </p>
            ) : (
              <ul className="divide-y divide-[hsl(var(--divider-subtle))]">
                {ollamaQuery.data?.models?.map((m) => (
                  <li key={m.name} className="py-2.5 font-mono text-sm">
                    {m.name}
                  </li>
                ))}
              </ul>
            )}
            {(() => {
              const detail = (ollamaQuery.data as { detail?: string } | undefined)
                ?.detail;
              return detail ? (
                <p className="text-sm text-[hsl(var(--muted-foreground))]">{detail}</p>
              ) : null;
            })()}
          </section>
        </TabsContent>
      </Tabs>
    </PageShell>
  );
}