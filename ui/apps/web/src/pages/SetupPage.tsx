import {
  ApiError,
  getOperatorKeyHint,
  getSystemDoctor,
  getSystemHealth,
  isValidOperatorApiKey,
  normalizeOperatorApiKey,
  repairAuditLogs,
  testApiConnection,
} from "@apxv/api-client";
import {
  ActionGroup,
  Alert,
  AlertDescription,
  Badge,
  Button,
  Input,
  Label,
  Panel,
  PanelBody,
  PanelHeader,
} from "@apxv/ui";
import { useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useApp } from "../context/AppContext";
import { BrandLogo } from "../components/BrandLogo";
import { integrityCheckFailed } from "../lib/doctor-format";
import {
  getApxvServerStatus,
  invokeTauri,
  isDockerDeploy,
  isTauri,
  type OperatorKeyInfo,
  type ServerStatus,
} from "../lib/tauri";

export function SetupPage() {
  const navigate = useNavigate();
  const { setApiKey, completeOnboarding } = useApp();

  const [apiKeyInput, setApiKeyInput] = useState("");
  const [operatorKey, setOperatorKey] = useState<OperatorKeyInfo | null>(null);
  const [keyLoadError, setKeyLoadError] = useState<string | null>(null);
  const [serverStatus, setServerStatus] = useState<ServerStatus | null>(null);
  const [serverMessage, setServerMessage] = useState<string | null>(null);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [doctorWarning, setDoctorWarning] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const isSetupPreview =
    typeof window !== "undefined" &&
    window.location.pathname === "/setup-preview";

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        if (isSetupPreview) {
          const previewKey =
            (window as Window & { __APXV_TEST_OPERATOR_KEY__?: string })
              .__APXV_TEST_OPERATOR_KEY__ ?? null;
          if (previewKey) {
            setOperatorKey({
              key: previewKey,
              file_path: "managed/config/OPERATOR-KEY-default-operator.txt",
              file_content: `API Key: ${previewKey}`,
              key_id: "default-operator",
            });
          }
        } else if (isTauri()) {
          const [keyInfo, status] = await Promise.all([
            invokeTauri<OperatorKeyInfo>("read_operator_key"),
            getApxvServerStatus(),
          ]);
          if (cancelled) return;
          setOperatorKey(keyInfo);
          setServerStatus(status);
          if (status.running) {
            setServerMessage(
              status.pid
                ? `API running (pid ${status.pid})`
                : "API running",
            );
          }
        } else if (isDockerDeploy()) {
          const keyInfo = await getOperatorKeyHint();
          if (cancelled) return;
          setOperatorKey(keyInfo);
        }
      } catch (err) {
        if (!cancelled) {
          setKeyLoadError((err as Error).message);
        }
      }

      try {
        await waitForHealth(45_000);
        if (!cancelled) {
          if (isTauri()) {
            const status = await getApxvServerStatus();
            setServerStatus(status);
            setServerMessage(
              status.running && status.pid
                ? `API ready (pid ${status.pid})`
                : "API ready",
            );
          } else {
            setServerStatus({ running: true, pid: null });
            setServerMessage(
              isDockerDeploy() ? "API ready (Docker)" : "API ready",
            );
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError((err as Error).message);
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [isSetupPreview]);

  function handleApiKeyChange(value: string) {
    setApiKeyInput(value);
    setError(null);
  }

  async function handleCopyKey() {
    if (!operatorKey) return;
    setCopyMessage(null);
    try {
      await navigator.clipboard.writeText(operatorKey.key);
      setCopyMessage("Copied to clipboard");
    } catch {
      setCopyMessage("Copy failed — select the key and copy manually");
    }
  }

  async function handleSaveKey() {
    if (!operatorKey) return;
    setSaveMessage(null);
    setBusy(true);
    try {
      if (isTauri()) {
        const path = await invokeTauri<string>("save_operator_key_file");
        setSaveMessage(`Saved to ${path}`);
      } else {
        const filename = operatorKey.key_id
          ? `OPERATOR-KEY-${operatorKey.key_id}.txt`
          : "OPERATOR-KEY-export.txt";
        const blob = new Blob([operatorKey.file_content], {
          type: "text/plain;charset=utf-8",
        });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = filename;
        anchor.click();
        URL.revokeObjectURL(url);
        setSaveMessage(`Downloaded ${filename}`);
      }
    } catch (err) {
      setSaveMessage((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleConnect() {
    setBusy(true);
    setError(null);
    setDoctorWarning(null);
    try {
      await waitForHealth(15_000);
      await setApiKey(apiKeyInput);
      try {
        await repairAuditLogs();
      } catch {
        // Quiet repair — doctor surfaces issues only when unhealthy.
      }
      await testApiConnection();
      const doctor = await getSystemDoctor(false);
      if (!doctor.healthy) {
        if (integrityCheckFailed(doctor.checks)) {
          setDoctorWarning(
            "Audit chain needs repair. Open System after connecting, or retry Connect.",
          );
        } else {
          setDoctorWarning(
            "Doctor reported issues. You can continue; review checks in System.",
          );
        }
      }
      await completeOnboarding();
      void navigate({ to: "/" });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? `${err.message} (${err.status})`
          : (err as Error).message;
      setError(message);
    } finally {
      setBusy(false);
    }
  }

  const normalized = normalizeOperatorApiKey(apiKeyInput) ?? "";
  const canConnect =
    !busy &&
    apiKeyInput.trim().length > 0 &&
    isValidOperatorApiKey(normalized);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[hsl(var(--background))] p-8">
      <div className="mb-10 text-center">
        <BrandLogo size="lg" className="inline-block" />
        <p className="mt-4 text-base text-[hsl(var(--muted-foreground))]">
          Governed local agents with cryptographic attestation
        </p>
      </div>

      <Panel className="w-full max-w-xl shadow-2xl shadow-black/20">
        <PanelHeader
          title="Setup"
          description="Connect to your local runtime with your operator API key."
        />
        <PanelBody className="space-y-5 pt-0">
          <div className="rounded-lg bg-[hsl(var(--surface-elevated))] px-4 py-4">
            <div className="mb-2 flex items-center justify-between gap-3">
              <p className="text-base font-medium">Runtime API</p>
              <Badge variant={serverStatus?.running ? "success" : "secondary"}>
                {serverStatus?.running ? "running" : "starting"}
              </Badge>
            </div>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              {serverMessage ??
                (isDockerDeploy()
                  ? "Waiting for API on :8741…"
                  : "Starting apxv_serve on :8741…")}
            </p>
          </div>

          <div className="space-y-3 rounded-lg border border-[hsl(var(--divider-subtle))] px-4 py-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-base font-medium">Your operator key</p>
              <ActionGroup>
                <Button
                  type="button"
                  variant="link"
                  className="h-auto px-0 py-0 text-xs"
                  onClick={() => void handleCopyKey()}
                  disabled={!operatorKey || busy}
                >
                  Copy
                </Button>
                <Button
                  type="button"
                  variant="link"
                  className="h-auto px-0 py-0 text-xs"
                  onClick={() => void handleSaveKey()}
                  disabled={!operatorKey || busy}
                >
                  Save to file
                </Button>
              </ActionGroup>
            </div>

            {operatorKey ? (
              <>
                <code className="block break-all rounded-md bg-[hsl(var(--surface-elevated))] px-3 py-2 font-mono text-sm">
                  {operatorKey.key}
                </code>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  From{" "}
                  <span className="font-mono">{operatorKey.file_path}</span>
                </p>
              </>
            ) : (
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                {keyLoadError ??
                  "Loading operator key from managed/config/OPERATOR-KEY-*.txt…"}
              </p>
            )}

            {copyMessage && (
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                {copyMessage}
              </p>
            )}
            {saveMessage && (
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                {saveMessage}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="api-key">Paste operator key</Label>
            <Input
              id="api-key"
              name="apxv-operator-api-key"
              type="text"
              spellCheck={false}
              autoCapitalize="off"
              autoCorrect="off"
              className="font-mono text-sm"
              value={apiKeyInput}
              onChange={(e) => handleApiKeyChange(e.target.value)}
              onPaste={(e) => {
                const pasted = e.clipboardData.getData("text");
                const normalizedPaste = normalizeOperatorApiKey(pasted);
                if (normalizedPaste) {
                  e.preventDefault();
                  handleApiKeyChange(normalizedPaste);
                }
              }}
              placeholder="Paste key from OPERATOR-KEY-*.txt"
              autoComplete="one-time-code"
              data-1p-ignore
              data-lpignore="true"
              data-form-type="other"
            />
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Paste once so you can save it. Next launch goes straight to the
              dashboard.
            </p>
          </div>

          <ActionGroup>
            <Button onClick={() => void handleConnect()} disabled={!canConnect}>
              {busy ? "Connecting…" : "Connect"}
            </Button>
          </ActionGroup>

          {doctorWarning && (
            <Alert variant="warning">
              <AlertDescription>{doctorWarning}</AlertDescription>
            </Alert>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </PanelBody>
      </Panel>
    </div>
  );
}

async function waitForHealth(timeoutMs: number): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  let lastError: Error | null = null;

  while (Date.now() < deadline) {
    try {
      await getSystemHealth();
      return;
    } catch (err) {
      lastError = err as Error;
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }

  throw new Error(
    lastError?.message ??
      "API did not respond on :8741. Check that apxv_serve started correctly.",
  );
}