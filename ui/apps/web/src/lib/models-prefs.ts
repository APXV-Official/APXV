/**
 * Operator-local model preferences (S3/S4).
 * Secrets stay in browser/local storage — never write cloud keys into Pipeline Spec.
 */

export type LlmMode = "local" | "cloud" | "demo";

export interface ModelsPrefs {
  mode: LlmMode;
  /** Ollama model name when mode=local */
  localModel: string;
  /** OpenAI-compatible base URL */
  cloudBaseUrl: string;
  /** Stored locally only */
  cloudApiKey: string;
  cloudModel: string;
}

const STORAGE_KEY = "apxv.modelsPrefs";
const LAST_PIPELINE_KEY = "apxv.lastPipelineId";

export const DEFAULT_MODELS_PREFS: ModelsPrefs = {
  mode: "local",
  localModel: "llama3.2",
  cloudBaseUrl: "https://api.openai.com/v1",
  cloudApiKey: "",
  cloudModel: "gpt-4o-mini",
};

export function loadModelsPrefs(): ModelsPrefs {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_MODELS_PREFS };
    const parsed = JSON.parse(raw) as Partial<ModelsPrefs>;
    return {
      ...DEFAULT_MODELS_PREFS,
      ...parsed,
      mode:
        parsed.mode === "cloud" || parsed.mode === "demo" || parsed.mode === "local"
          ? parsed.mode
          : "local",
    };
  } catch {
    return { ...DEFAULT_MODELS_PREFS };
  }
}

export function saveModelsPrefs(prefs: ModelsPrefs): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
}

/** Payload fragment for composition / pipeline run. */
export function llmPayloadFromPrefs(prefs: ModelsPrefs = loadModelsPrefs()): {
  backend: string;
  model: string;
} {
  if (prefs.mode === "demo") {
    return { backend: "simulated", model: "simulated" };
  }
  if (prefs.mode === "cloud") {
    // Runtime currently resolves ollama | simulated; cloud key is operator-side future.
    // Send open-compatible markers for API extensions; fall back to ollama model field.
    return {
      backend: "ollama",
      model: prefs.cloudModel || prefs.localModel || "llama3.2",
    };
  }
  return {
    backend: "ollama",
    model: prefs.localModel || "llama3.2",
  };
}

export function modeLabel(mode: LlmMode): string {
  if (mode === "cloud") return "Cloud (leaves this machine)";
  if (mode === "demo") return "Demo (simulated)";
  return "Local (Ollama)";
}

export function rememberLastPipelineId(id: string | undefined | null): void {
  if (!id) {
    localStorage.removeItem(LAST_PIPELINE_KEY);
    return;
  }
  localStorage.setItem(LAST_PIPELINE_KEY, id);
}

export function loadLastPipelineId(): string | null {
  return localStorage.getItem(LAST_PIPELINE_KEY);
}
