import {
  getSystemDoctor,
  getSystemHealth,
  isValidOperatorApiKey,
  normalizeOperatorApiKey,
  repairAuditLogs,
  testApiConnection,
} from "@apxv/api-client";

import type { OnboardingStep } from "@apxv/types";
import {
  ActionGroup,
  Alert,
  AlertDescription,
  AlertTitle,
  Badge,
  Button,
  Input,
  Label,
  Panel,
  PanelBody,
  PanelHeader,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@apxv/ui";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { useApp } from "../context/AppContext";
import {
  formatDoctorCheckSummary,
  integrityCheckFailed,
} from "../lib/doctor-format";
import { BrandLogo } from "../components/BrandLogo";
import { OperatorKeyPanel } from "../components/OperatorKeyPanel";
import { formatApiError } from "../lib/api-errors";
import { parseOnboardingRedirect } from "../lib/onboarding-nav";
import {
  discoverOperatorKey,
  type DiscoveredOperatorKey,
} from "../lib/operator-key-discovery";
import { PACK_TUTORIAL_URL } from "../lib/pack-studio";
import {
  ensureApxvServerStarted,
  formatServerStatus,
  getApxvServerStatus,
  getDefaultApxvRoot,
  isTauri,
  type ServerStatus,
} from "../lib/tauri";
import { waitForHealth } from "../lib/wait-for-health";
import { router } from "../router";

const STEPS: OnboardingStep[] = ["welcome", "connect", "doctor", "complete"];

export function OnboardingPage() {
  const navigate = useNavigate();
  const { redirect } = useSearch({ strict: false });
  const { apiKey, onboarded, setApiKey, completeOnboarding, resetOnboarding } =
    useApp();

  const [step, setStep] = useState<OnboardingStep>(
    apiKey && !onboarded ? "connect" : "welcome",
  );
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [keyRejected, setKeyRejected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [serverMessage, setServerMessage] = useState<string | null>(null);
  const [serverStatus, setServerStatus] = useState<ServerStatus | null>(null);
  const [apxvRoot, setApxvRoot] = useState<string | null>(null);
  const [doctorChecks, setDoctorChecks] = useState<
    Awaited<ReturnType<typeof getSystemDoctor>>["checks"] | null
  >(null);
  const [repairMessage, setRepairMessage] = useState<string | null>(null);
  const [operatorKey, setOperatorKey] = useState<DiscoveredOperatorKey | null>(
    null,
  );
  const [keyLoadError, setKeyLoadError] = useState<string | null>(null);

  const stepIndex = STEPS.indexOf(step);
  const normalized = normalizeOperatorApiKey(apiKeyInput) ?? "";
  const keyValid = isValidOperatorApiKey(normalized);
  const keyInvalid = apiKeyInput.trim().length > 0 && !keyValid;

  const reloadOperatorKey = useCallback(async () => {
    setKeyLoadError(null);
    const result = await discoverOperatorKey();
    if (result.status === "found") {
      setOperatorKey(result.key);
      setApiKeyInput((prev) => prev.trim() || result.key.key);
    } else {
      setOperatorKey(null);
      if (result.status === "unreachable") {
        setKeyLoadError(
          `API not reachable — ${result.message} Start apxv_serve, then reload.`,
        );
      } else {
        setKeyLoadError(
          "Start apxv_serve, then reload — or paste OPERATOR-KEY-*.txt manually.",
        );
      }
    }
  }, []);

  useEffect(() => {
    if (step !== "connect") return;
    void reloadOperatorKey();
    const normalizedStored = apiKey ? normalizeOperatorApiKey(apiKey) : null;
    if (apiKey && !normalizedStored) {
      void resetOnboarding().then(() => {
        setApiKeyInput("");
        setKeyRejected(true);
      });
      return;
    }
    if (normalizedStored) {
      setApiKeyInput(normalizedStored);
    }
  }, [step, apiKey, resetOnboarding, reloadOperatorKey]);

  useEffect(() => {
    if (!isTauri() || step !== "connect") return;
    let cancelled = false;
    void (async () => {
      try {
        const status = await getApxvServerStatus();
        if (!cancelled) {
          setServerStatus(status);
          setServerMessage(formatServerStatus(status));
        }
      } catch {
        // Server status is optional on connect step.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [step]);

  async function handleClearKey() {
    await resetOnboarding();
    setApiKeyInput("");
    setKeyRejected(false);
    setError(null);
  }

  function handleApiKeyChange(value: string) {
    setApiKeyInput(value);
    setKeyRejected(false);
    setError(null);
  }

  useEffect(() => {
    if (!isTauri()) return;
    void getDefaultApxvRoot().then(setApxvRoot);
  }, []);

  async function handleStartServer() {
    if (!isTauri()) return;
    setBusy(true);
    setError(null);
    setServerMessage(null);
    try {
      const result = await ensureApxvServerStarted();
      setServerMessage(result);
      await getSystemHealth();
      const status = await getApxvServerStatus();
      setServerStatus(status);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleTestConnection() {
    setBusy(true);
    setError(null);
    try {
      await waitForHealth(15_000);
      await setApiKey(apiKeyInput);
      await testApiConnection();
      setStep("doctor");
    } catch (err) {
      setKeyRejected(true);
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleRunDoctor() {
    setBusy(true);
    setError(null);
    setRepairMessage(null);
    try {
      const result = await getSystemDoctor(false);
      setDoctorChecks(result.checks);
      if (!result.healthy) {
        if (integrityCheckFailed(result.checks)) {
          setError(
            "Audit log chain is broken (often from heavy API use). Click Repair audit chain, then re-run doctor.",
          );
        } else {
          setError("Doctor reported issues — review checks below before continuing.");
        }
      } else {
        setStep("complete");
      }
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleRepairAudit() {
    setBusy(true);
    setError(null);
    setRepairMessage(null);
    try {
      const result = await repairAuditLogs();
      const fixed = result.repair.all_valid;
      setRepairMessage(
        fixed
          ? "Audit chains repaired. Re-run doctor to confirm."
          : "Repair finished but some logs may still need attention.",
      );
      if (fixed) {
        const doctor = await getSystemDoctor(false);
        setDoctorChecks(doctor.checks);
        if (doctor.healthy) {
          setStep("complete");
          setError(null);
        }
      }
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleFinish() {
    await completeOnboarding();
    await router.invalidate();
    const redirectTo = typeof redirect === "string" ? redirect : undefined;
    const target = parseOnboardingRedirect(redirectTo);
    await navigate({ to: target.to, search: target.search });
  }

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
          title="Operator setup"
          description="Connect to your local air-gapped runtime with an operator API key."
        />
        <PanelBody className="space-y-5 pt-0">
          <ActionGroup>
            {STEPS.map((s, i) => (
              <Badge
                key={s}
                variant={i <= stepIndex ? "default" : "secondary"}
                className="capitalize"
              >
                {s}
              </Badge>
            ))}
          </ActionGroup>

          {step === "welcome" && (
            <>
              <p className="text-[0.9375rem] leading-relaxed text-[hsl(var(--muted-foreground))]">
                Start the API server, then paste your operator key from{" "}
                <code className="rounded-md bg-[hsl(var(--surface-elevated))] px-1.5 py-0.5 text-sm">
                  managed/config/OPERATOR-KEY-*.txt
                </code>{" "}
                or create one in Settings after connecting.
              </p>
              {!isTauri() && (
                <div className="rounded-lg bg-[hsl(var(--surface-elevated))] px-4 py-3 text-sm text-[hsl(var(--muted-foreground))]">
                  Run{" "}
                  <code className="rounded-md bg-[hsl(var(--overlay-muted))] px-1.5 py-0.5">
                    python -m scripts.apxv_serve
                  </code>{" "}
                  in the APXV folder before testing your connection.
                </div>
              )}
              {isTauri() && (
                <div className="rounded-lg bg-[hsl(var(--surface-elevated))] px-4 py-4">
                  <p className="mb-2 text-base font-medium">Desktop: start runtime</p>
                  <p className="mb-3 text-sm text-[hsl(var(--muted-foreground))]">
                    Launch apxv_serve from {apxvRoot ?? "your local APXV folder"}
                  </p>
                  <ActionGroup>
                    <Button
                      variant="link"
                      onClick={() => void handleStartServer()}
                      disabled={busy}
                    >
                      Start APXV server
                    </Button>
                  </ActionGroup>
                  {serverMessage && (
                    <p className="mt-3 text-sm text-[hsl(var(--muted-foreground))]">
                      {serverMessage}
                    </p>
                  )}
                </div>
              )}
              <ActionGroup>
                <Button onClick={() => setStep("connect")}>Continue</Button>
              </ActionGroup>
            </>
          )}

          {step === "connect" && (
            <>
              <div className="rounded-lg bg-[hsl(var(--surface-elevated))] px-4 py-4">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <p className="text-base font-medium">Runtime API</p>
                  <Badge variant={serverStatus?.port_open ? "success" : "secondary"}>
                    {serverStatus?.port_open ? "ready" : "starting"}
                  </Badge>
                </div>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">
                  {serverMessage ??
                    (isTauri()
                      ? "Starting apxv_serve on :8741…"
                      : "Waiting for API on :8741…")}
                </p>
              </div>

              <OperatorKeyPanel
                operatorKey={operatorKey}
                loadError={keyLoadError}
                busy={busy}
                onUseKey={(key) => handleApiKeyChange(key)}
                onReload={() => void reloadOperatorKey()}
              />
              {keyRejected && (
                <Alert variant="warning">
                  <AlertDescription>
                    Connection failed. Click <strong>Clear field</strong>, then paste
                    the key line from{" "}
                    <code className="rounded-md bg-[hsl(var(--overlay-muted))] px-1.5 py-0.5 text-sm">
                      OPERATOR-KEY-*.txt
                    </code>{" "}
                    (not password-manager dots).
                  </AlertDescription>
                </Alert>
              )}
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <Label htmlFor="api-key">Operator API key</Label>
                  <Button
                    type="button"
                    variant="link"
                    className="h-auto px-0 py-0 text-xs"
                    onClick={() => void handleClearKey()}
                    disabled={busy}
                  >
                    Clear field
                  </Button>
                </div>
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
                  Paste the{" "}
                  <code className="rounded bg-[hsl(var(--overlay-muted))] px-1">
                    API Key:
                  </code>{" "}
                  line from the file, or the whole file — we extract it automatically.
                </p>
                {keyInvalid && (
                  <p className="text-xs text-[hsl(var(--destructive))]">
                    Paste the full operator key from OPERATOR-KEY-*.txt (43+ characters).
                  </p>
                )}
              </div>
              <ActionGroup>
                <Button
                  variant="link"
                  onClick={() => setStep("welcome")}
                  disabled={busy}
                >
                  Back
                </Button>
                <Button
                  onClick={() => void handleTestConnection()}
                  disabled={busy || !apiKeyInput.trim() || !keyValid}
                >
                  {busy ? "Testing…" : "Test connection"}
                </Button>
              </ActionGroup>
            </>
          )}

          {step === "doctor" && (
            <>
              <p className="text-[0.9375rem] text-[hsl(var(--muted-foreground))]">
                Run a full system doctor check before entering the dashboard.
              </p>
              {integrityCheckFailed(doctorChecks) && (
                <Alert variant="warning">
                  <AlertTitle>Audit chain needs repair</AlertTitle>
                  <AlertDescription>
                    The system audit log chain broke — usually from concurrent API
                    requests before a recent fix. This is repairable in one click and
                    does not delete your artifacts or jobs.
                  </AlertDescription>
                </Alert>
              )}
              {repairMessage && (
                <Alert variant="success">
                  <AlertDescription>{repairMessage}</AlertDescription>
                </Alert>
              )}
              {doctorChecks && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Check</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Detail</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {doctorChecks.map((check) => (
                      <TableRow key={check.name}>
                        <TableCell className="font-mono">{check.name}</TableCell>
                        <TableCell>
                          <Badge variant={check.ok ? "success" : "destructive"}>
                            {check.ok ? "ok" : "fail"}
                          </Badge>
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
              <ActionGroup>
                <Button
                  variant="link"
                  onClick={() => setStep("connect")}
                  disabled={busy}
                >
                  Back
                </Button>
                <Button onClick={() => void handleRunDoctor()} disabled={busy}>
                  {busy ? "Running…" : doctorChecks ? "Re-run doctor" : "Run doctor"}
                </Button>
                {integrityCheckFailed(doctorChecks) && (
                  <Button
                    variant="default"
                    onClick={() => void handleRepairAudit()}
                    disabled={busy}
                  >
                    {busy ? "Repairing…" : "Repair audit chain"}
                  </Button>
                )}
                {doctorChecks && (
                  <Button variant="link" onClick={() => setStep("complete")}>
                    Continue anyway
                  </Button>
                )}
              </ActionGroup>
            </>
          )}

          {step === "complete" && (
            <>
              <p className="text-[0.9375rem] text-[hsl(var(--muted-foreground))]">
                Setup complete. The dashboard will show live health and integrity
                status.
              </p>
              <ActionGroup>
                <Button onClick={() => void handleFinish()}>Open dashboard</Button>
              </ActionGroup>
            </>
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