import { APXV_API_DEFAULT_BASE } from "@apxv/types";

export function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export function isDockerDeploy(): boolean {
  return import.meta.env.VITE_APXV_DOCKER === "true";
}

/** Desktop (Tauri) or Docker nginx — use Setup page instead of browser wizard. */
export function usesSetupFlow(): boolean {
  return isTauri() || isDockerDeploy();
}

export function getFirstRunPath(): "/bootstrap" | "/setup" | "/onboarding" {
  if (isTauri()) return "/bootstrap";
  return usesSetupFlow() ? "/setup" : "/onboarding";
}

export function getDefaultBaseUrl(): string {
  if (import.meta.env.DEV || isDockerDeploy()) {
    return "";
  }
  return APXV_API_DEFAULT_BASE;
}

export interface ServerStatus {
  running: boolean;
  pid: number | null;
}

export interface OperatorKeyInfo {
  key: string;
  file_path: string;
  file_content: string;
  key_id: string | null;
}

export interface BootstrapStatus {
  apxv_root: string;
  source_root: string;
  runtime_ready: boolean;
  running: boolean;
  sovereign_setup: boolean;
  bootstrap_complete: boolean;
  partial: boolean;
  install_json: Record<string, unknown> | null;
  exit_code: number | null;
  last_lines: string[];
  error: string | null;
}

export async function invokeTauri<T>(
  command: string,
  args?: Record<string, unknown>,
): Promise<T> {
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke<T>(command, args);
}

export async function getDefaultApxvRoot(): Promise<string> {
  if (isTauri()) {
    return invokeTauri<string>("get_default_apxv_root");
  }
  const { DEFAULT_APXV_ROOT } = await import("@apxv/types");
  return DEFAULT_APXV_ROOT;
}

export async function getApxvServerStatus(): Promise<ServerStatus> {
  return invokeTauri<ServerStatus>("get_apxv_server_status");
}

export async function ensureApxvServerStarted(): Promise<string> {
  return invokeTauri<string>("start_apxv_server");
}

export async function getBootstrapStatus(): Promise<BootstrapStatus> {
  return invokeTauri<BootstrapStatus>("get_bootstrap_status");
}

export async function runBootstrap(options?: {
  skipOllama?: boolean;
  skipVoice?: boolean;
}): Promise<string> {
  return invokeTauri<string>("run_bootstrap", {
    skipOllama: options?.skipOllama ?? false,
    skipVoice: options?.skipVoice ?? false,
  });
}