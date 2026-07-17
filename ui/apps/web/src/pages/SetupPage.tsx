import {
  getSystemDoctor,
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
import { useNavigate, useSearch } from "@tanstack/react-router";
import { router } from "../router";
import { useCallback, useEffect, useState } from "react";
import { formatApiError } from "../lib/api-errors";
import { isOnboardingComplete } from "../lib/auth-storage";
import { useApp } from "../context/AppContext";
import { BrandLogo } from "../components/BrandLogo";
import { OperatorKeyPanel } from "../components/OperatorKeyPanel";
import { integrityCheckFailed } from "../lib/doctor-format";
import { parseOnboardingRedirect } from "../lib/onboarding-nav";
import {
  discoverOperatorKey,
  type DiscoveredOperatorKey,
} from "../lib/operator-key-discovery";
import { PACK_TUTORIAL_URL } from "../lib/pack-studio";
import { waitForHealth } from "../lib/wait-for-health";
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
  const { redirect } = useSearch({ strict: false });
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
  const [testing, setTesting] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [autoFilled, setAutoFilled] = useState(false);
  const busy = testing || connecting;

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
        setApiKeyInput((prev) => {
          if (prev.trim()) return prev;
          setAutoFilled(true);
          return previewKey;
        });
      }
      return;
    }

    const result = await discoverOperatorKey();
    if (result.status === "found") {
      setOperatorKey(result.key);
      setApiKeyInput((prev) => {
        if (prev.trim()) return prev;
        setAutoFilled(true);
        return result.key.key;
      });
    } else {
      setOperatorKey(null);
      if (result.status === "unreachable") {
        setKeyLoadError(
          `API not reachable — ${result.message} Start apxv_serve, then reload.`,
        );
      } else {
        setKeyLoadError(
          "No OPERATOR-KEY-*.txt found under managed/config. Run bootstrap or setup_first_run.",
        );
      }
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
        const redirectTo =
          typeof redirect === "string" ? redirect : undefined;
        const target = parseOnboardingRedirect(redirectTo);
        await navigate({ to: target.to, search: target.search });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isSetupPreview, navigate, redirect]);

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
    setApiKeyInput(normalizeOperatorApiKey(value) ?? value);
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
    const exportKey = operatorKey ?? buildExportKeyFromInput(apiKeyInput);
    if (!exportKey) return;
    setSaveMessage(null);
    setConnecting(true);
    try {
      if (isTauri()) {
        const path = await invokeTauri<string>("save_operator_key_file");
        setSaveMessage(`Saved to ${path}`);
      } else {
        const filename = exportKey.key_id
          ? `OPERATOR-KEY-${exportKey.key_id}.txt`
          : "OPERATOR-KEY-export.txt";
        const blob = new Blob([exportKey.file_content], {
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
      setSaveMessage(formatApiError(err));
    } finally {
      setConnecting(false);
    }
  }

  async function handleTestConnection() {
    setTesting(true);
    setError(null);
    setTestMessage(null);
    try {
      await waitForHealth(15_000);
      await setApiKey(apiKeyInput);
      await testApiConnection();
      setTestMessage("Connection OK — API accepted your operator key.");
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setTesting(false);
    }
  }

  async function handleConnect() {
    setConnecting(true);
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
      const redirectTo =
        typeof redirect === "string" ? redirect : undefined;
      const target = parseOnboardingRedirect(redirectTo);
      await navigate({ to: target.to, search: target.search });
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setConnecting(false);
    }
  }

  const normalized = normalizeOperatorApiKey(apiKeyInput) ?? "";
  const keyValid = isValidOperatorApiKey(normalized);
  const keyInvalid = apiKeyInput.trim().length > 0 && !keyValid;
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
            {keyInvalid && (
              <p className="text-xs text-[hsl(var(--destructive))]">
                Paste the full operator key from OPERATOR-KEY-*.txt (43+ characters).
              </p>
            )}
          </div>

          <ActionGroup>
            <Button
              variant="secondary"
              onClick={() => void handleTestConnection()}
              disabled={!canTest}
            >
              {testing ? "Testing…" : "Test connection"}
            </Button>
            <Button onClick={() => void handleConnect()} disabled={!canConnect}>
              {connecting ? "Connecting…" : connectLabel}
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

          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            New operator?{" "}
            <a
              href={PACK_TUTORIAL_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2"
            >
              BUILD-YOUR-FIRST-PACK guide
            </a>
          </p>
        </PanelBody>
      </Panel>
    </div>
  );
}

function buildExportKeyFromInput(
  input: string,
): DiscoveredOperatorKey | null {
  const normalized = normalizeOperatorApiKey(input);
  if (!normalized || !isValidOperatorApiKey(normalized)) return null;
  return {
    key: normalized,
    file_path: "managed/config/OPERATOR-KEY-export.txt",
    file_content: `API Key: ${normalized}`,
    key_id: "export",
  };
}