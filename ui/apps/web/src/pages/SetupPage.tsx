import {
  ApiError,
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
import { router } from "../router";
import { useCallback, useEffect, useState } from "react";
import { isOnboardingComplete } from "../lib/auth-storage";
import { useApp } from "../context/AppContext";
import { BrandLogo } from "../components/BrandLogo";
import { OperatorKeyPanel } from "../components/OperatorKeyPanel";
import { integrityCheckFailed } from "../lib/doctor-format";
import {
  discoverOperatorKey,
  type DiscoveredOperatorKey,
} from "../lib/operator-key-discovery";
import {
  formatServerStatus,
  getApxvServerStatus,
  invokeTauri,
  isDockerDeploy,
  isTauri,
  quitApxvDesktop,
  type ServerStatus,
} from "../lib/tauri";

export function SetupPage() {
  const navigate = useNavigate();
  const { setApiKey, completeOnboarding } = useApp();

  const [apiKeyInput, setApiKeyInput] = useState("");
  const [operatorKey, setOperatorKey] = useState<DiscoveredOperatorKey | null>(null);
  const [keyLoadError, setKeyLoadError] = useState<string | null>(null);
  const [serverStatus, setServerStatus] = useState<ServerStatus | null>(null);
  const [serverMessage, setServerMessage] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [testMessage, setTestMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [doctorWarning, setDoctorWarning] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [autoFilled, setAutoFilled] = useState(false);

  const isSetupPreview =
    typeof window !== "undefined" &&
    window.location.pathname === "/setup-preview";

  const reloadOperatorKey = useCallback(async () => {
    setKeyLoadError(null);
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
      return;
    }

    const discovered = await discoverOperatorKey();
    if (discovered) {
      setOperatorKey(discovered);
      setApiKeyInput((prev) => {
        if (prev.trim()) return prev;
        setAutoFilled(true);
        return discovered.key;
      });
    } else {
      setOperatorKey(null);
      setKeyLoadError(
        "No OPERATOR-KEY-*.txt found under managed/config. Run bootstrap or setup_first_run.",
      );
    }
  }, [isSetupPreview]);

  useEffect(() => {
    if (isSetupPreview || !isTauri()) return;
    let cancelled = false;
    void (async () => {
      if (!(await isOnboardingComplete())) return;
      router.update({
        context: {
          onboarded: true,
          sovereignReady: router.options.context?.sovereignReady ?? true,
        },
      });
      await router.invalidate();
      if (!cancelled) {
        await navigate({ to: "/" });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isSetupPreview, navigate]);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        if (isTauri()) {
          const status = await getApxvServerStatus();
          if (cancelled) return;
          setServerStatus(status);
          setServerMessage(formatServerStatus(status));
        }
        await reloadOperatorKey();
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
            setServerMessage(formatServerStatus(status));
          } else {
            setServerStatus({
              running: true,
              pid: null,
              port_open: true,
              managed: false,
            });
            setServerMessage(
              isDockerDeploy() ? "API ready (Docker)" : "API ready",
            );
          }
          await reloadOperatorKey();
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
  }, [isSetupPreview, reloadOperatorKey]);

  function handleApiKeyChange(value: string) {
    setApiKeyInput(value);
    setAutoFilled(false);
    setError(null);
    setTestMessage(null);
  }

  function handleUseDiscoveredKey(key: string) {
    setApiKeyInput(key);
    setAutoFilled(true);
    setError(null);
    setTestMessage(null);
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

  async function handleTestConnection() {
    setBusy(true);
    setError(null);
    setTestMessage(null);
    try {
      await waitForHealth(15_000);
      await setApiKey(apiKeyInput);
      await testApiConnection();
      setTestMessage("Connection OK — API accepted your operator key.");
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

  async function handleConnect() {
    setBusy(true);
    setError(null);
    setDoctorWarning(null);
    setTestMessage(null);
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
      await router.invalidate();
      await navigate({ to: "/" });
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
  const keyValid = isValidOperatorApiKey(normalized);
  const canTest = !busy && apiKeyInput.trim().length > 0 && keyValid;
  const canConnect = canTest;
  const connectLabel =
    autoFilled && operatorKey
      ? "Connect with discovered key"
      : "Connect";

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
          title="Connect"
          description="Your operator key was created during bootstrap — we load it automatically when possible."
        />
        <PanelBody className="space-y-5 pt-0">
          <div className="rounded-lg bg-[hsl(var(--surface-elevated))] px-4 py-4">
            <div className="mb-2 flex items-center justify-between gap-3">
              <p className="text-base font-medium">Runtime API</p>
              <Badge variant={serverStatus?.port_open ? "success" : "secondary"}>
                {serverStatus?.port_open ? "ready" : "starting"}
              </Badge>
            </div>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              {serverMessage ??
                (isDockerDeploy()
                  ? "Waiting for API on :8741…"
                  : "Starting apxv_serve on :8741…")}
            </p>
          </div>

          <OperatorKeyPanel
            operatorKey={operatorKey}
            loadError={keyLoadError}
            busy={busy}
            onUseKey={handleUseDiscoveredKey}
            onSaveKey={() => void handleSaveKey()}
            saveMessage={saveMessage}
            showSave
            onReload={() => void reloadOperatorKey()}
          />

          <div className="space-y-2">
            <Label htmlFor="api-key">Operator API key</Label>
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
              placeholder="Auto-filled from OPERATOR-KEY-*.txt when available"
              autoComplete="one-time-code"
              data-1p-ignore
              data-lpignore="true"
              data-form-type="other"
            />
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              {autoFilled
                ? "Key loaded from your runtime. Test connection, then Connect to enter the dashboard."
                : "Paste the API Key line if auto-discovery did not run yet."}
            </p>
          </div>

          <ActionGroup>
            <Button
              variant="secondary"
              onClick={() => void handleTestConnection()}
              disabled={!canTest}
            >
              {busy ? "Testing…" : "Test connection"}
            </Button>
            <Button onClick={() => void handleConnect()} disabled={!canConnect}>
              {busy ? "Connecting…" : connectLabel}
            </Button>
            {isTauri() && (
              <Button
                variant="link"
                disabled={busy}
                onClick={() => void quitApxvDesktop()}
              >
                Quit APXV
              </Button>
            )}
          </ActionGroup>

          {testMessage && (
            <Alert variant="success">
              <AlertDescription>{testMessage}</AlertDescription>
            </Alert>
          )}

          {isTauri() && (
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              Closing the window keeps APXV in the tray. Use Quit APXV or the tray
              menu to stop the API and exit.
            </p>
          )}

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