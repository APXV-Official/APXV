import {
  ActionGroup,
  Alert,
  AlertDescription,
  Badge,
  Button,
  Checkbox,
  Label,
  Panel,
  PanelBody,
  PanelHeader,
} from "@apxv/ui";
import { useNavigate } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { BrandLogo } from "../components/BrandLogo";
import { readOnboardedSync } from "../lib/auth-storage";
import {
  ensureApxvServerStarted,
  getBootstrapStatus,
  isTauri,
  runBootstrap,
  type BootstrapStatus,
} from "../lib/tauri";
import { router } from "../router";

const STEPS = [
  { id: "zk", label: "ZK trusted setup", detail: "11 circuits — your proving keys" },
  { id: "runtime", label: "Runtime init", detail: "Policy, governance, operator key" },
  { id: "ollama", label: "Ollama (optional)", detail: "Local LLM for AI Governance pack" },
  { id: "voice", label: "Vosk voice (optional)", detail: "Speech-to-text workflows" },
  { id: "smoke", label: "First proof", detail: "Doctor, integrity, attest smoke" },
] as const;

export function BootstrapPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<BootstrapStatus | null>(null);
  const [skipOllama, setSkipOllama] = useState(false);
  const [skipVoice, setSkipVoice] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isPreview =
    typeof window !== "undefined" &&
    window.location.pathname === "/bootstrap-preview";

  const refreshStatus = useCallback(async () => {
    if (isPreview) {
      const preview = (
        window as Window & { __APXV_BOOTSTRAP_PREVIEW__?: BootstrapStatus }
      ).__APXV_BOOTSTRAP_PREVIEW__;
      if (preview) {
        setStatus(preview);
      }
      return;
    }
    if (!isTauri()) return;
    const next = await getBootstrapStatus();
    setStatus(next);
    if (next.bootstrap_complete) {
      if (isTauri()) {
        try {
          await ensureApxvServerStarted();
        } catch {
          // Setup page retries health wait.
        }
      }
      router.update({
        context: {
          onboarded: readOnboardedSync(),
          sovereignReady: true,
        },
      });
      void navigate({ to: "/setup", search: { redirect: undefined } });
    }
  }, [isPreview, navigate]);

  useEffect(() => {
    void refreshStatus();
    pollRef.current = setInterval(() => {
      void refreshStatus();
    }, 1500);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [refreshStatus]);

  async function handleStart() {
    setBusy(true);
    setError(null);
    try {
      if (isPreview) {
        (
          window as Window & { __APXV_BOOTSTRAP_PREVIEW__?: BootstrapStatus }
        ).__APXV_BOOTSTRAP_PREVIEW__ = {
          apxv_root: "%LOCALAPPDATA%\\APXV",
          source_root: "runtime",
          runtime_ready: true,
          running: true,
          sovereign_setup: false,
          bootstrap_complete: false,
          partial: false,
          install_json: null,
          exit_code: null,
          last_lines: ["[1/9] Preflight", "[3/9] Governance ZK trusted setup"],
          error: null,
        };
        await refreshStatus();
        return;
      }
      await runBootstrap({ skipOllama, skipVoice });
      await refreshStatus();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const running = status?.running ?? false;
  const complete = status?.bootstrap_complete ?? false;
  const canStart = !busy && !running && !complete;

  function activeStepIndex(): number {
    if (!status?.running && !status?.sovereign_setup) return -1;
    const lines = (status?.last_lines ?? []).join("\n").toLowerCase();
    if (lines.includes("smoke") || lines.includes("[9/9]")) return 4;
    if (lines.includes("voice") || lines.includes("[7/9]")) return 3;
    if (lines.includes("ollama") || lines.includes("[6/9]")) return 2;
    if (lines.includes("first-run") || lines.includes("[5/9]")) return 1;
    if (lines.includes("zk") || lines.includes("[3/9]") || lines.includes("[4/9]")) {
      return 0;
    }
    return status?.running ? 0 : -1;
  }

  const stepIndex = activeStepIndex();

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[hsl(var(--background))] p-8">
      <div className="mb-10 text-center">
        <BrandLogo size="lg" className="inline-block" />
        <p className="mt-4 text-base text-[hsl(var(--muted-foreground))]">
          Sovereign setup — your machine generates your proving keys
        </p>
      </div>

      <Panel className="w-full max-w-2xl shadow-2xl shadow-black/20">
        <PanelHeader
          title="Bootstrap"
          description="First launch runs trusted setup locally. This typically takes 20–60 minutes."
        />
        <PanelBody className="space-y-5 pt-0">
          <div className="rounded-lg bg-[hsl(var(--surface-elevated))] px-4 py-4">
            <div className="mb-2 flex items-center justify-between gap-3">
              <p className="text-base font-medium">Data location</p>
              <Badge variant="secondary">local only</Badge>
            </div>
            <p className="font-mono text-sm text-[hsl(var(--muted-foreground))]">
              {status?.apxv_root ?? "%LOCALAPPDATA%\\APXV"}
            </p>
          </div>

          <ol className="space-y-3">
            {STEPS.map((step, index) => {
              const done = complete || (stepIndex >= 0 && index < stepIndex);
              const active = running && index === stepIndex;
              return (
                <li
                  key={step.id}
                  className="flex items-start gap-3 rounded-lg border border-[hsl(var(--divider-subtle))] px-4 py-3"
                >
                  <Badge
                    variant={done ? "success" : active ? "default" : "secondary"}
                    className="mt-0.5 shrink-0"
                  >
                    {done ? "done" : active ? "active" : String(index + 1)}
                  </Badge>
                  <div>
                    <p className="text-sm font-medium">{step.label}</p>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                      {step.detail}
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>

          {!running && !complete && (
            <div className="space-y-3 rounded-lg border border-[hsl(var(--divider-subtle))] px-4 py-4">
              <p className="text-sm font-medium">Optional integrations</p>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="skip-ollama"
                  checked={skipOllama}
                  onChange={(e) => setSkipOllama(e.target.checked)}
                  disabled={busy}
                />
                <Label htmlFor="skip-ollama" className="text-sm font-normal">
                  Skip Ollama (disable AI Governance pack until configured)
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="skip-voice"
                  checked={skipVoice}
                  onChange={(e) => setSkipVoice(e.target.checked)}
                  disabled={busy}
                />
                <Label htmlFor="skip-voice" className="text-sm font-normal">
                  Skip Vosk voice model download
                </Label>
              </div>
            </div>
          )}

          {status?.last_lines && status.last_lines.length > 0 && (
            <div className="max-h-40 overflow-y-auto rounded-md bg-[hsl(var(--surface-elevated))] p-3 font-mono text-xs text-[hsl(var(--muted-foreground))]">
              {status.last_lines.slice(-12).map((line) => (
                <div key={line}>{line}</div>
              ))}
            </div>
          )}

          {status?.sovereign_setup &&
            status.install_json &&
            "vk_hashes" in status.install_json && (
            <Alert>
              <AlertDescription>
                Sovereign setup complete. Your verification key hashes are unique
                to this machine.
              </AlertDescription>
            </Alert>
          )}

          {status?.partial && (
            <Alert variant="warning">
              <AlertDescription>
                Bootstrap finished with optional integrations incomplete. You can
                repair them later in Settings.
              </AlertDescription>
            </Alert>
          )}

          <ActionGroup>
            <Button onClick={() => void handleStart()} disabled={!canStart}>
              {running
                ? "Bootstrap running…"
                : complete
                  ? "Continue to setup"
                  : busy
                    ? "Starting…"
                    : "Start sovereign bootstrap"}
            </Button>
            {complete && (
              <Button
                variant="secondary"
                onClick={() =>
                  void navigate({ to: "/setup", search: { redirect: undefined } })
                }
              >
                Open setup
              </Button>
            )}
          </ActionGroup>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {status?.error && (
            <Alert variant="destructive">
              <AlertDescription>{status.error}</AlertDescription>
            </Alert>
          )}
        </PanelBody>
      </Panel>
    </div>
  );
}