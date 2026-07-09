import {
  configureApi,
  getSystemHealth,
  normalizeOperatorApiKey,
} from "@apxv/api-client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  clearApiKey,
  isOnboardingComplete,
  loadApiKey,
  saveApiKey,
  setOnboardingComplete,
} from "../lib/auth-storage";
import {
  ensureApxvServerStarted,
  getBootstrapStatus,
  getDefaultBaseUrl,
  isTauri,
} from "../lib/tauri";
import { router } from "../router";

interface AppContextValue {
  ready: boolean;
  sovereignReady: boolean;
  apiKey: string | null;
  onboarded: boolean;
  setApiKey: (key: string) => Promise<void>;
  completeOnboarding: () => Promise<void>;
  resetOnboarding: () => Promise<void>;
  invalidateSession: () => Promise<void>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [sovereignReady, setSovereignReady] = useState(!isTauri());
  const [apiKey, setApiKeyState] = useState<string | null>(null);
  const [onboarded, setOnboarded] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const [key, complete] = await Promise.all([
        loadApiKey(),
        isOnboardingComplete(),
      ]);

      if (cancelled) return;

      const normalizedKey = key ? normalizeOperatorApiKey(key) : null;
      if (key && !normalizedKey) {
        await clearApiKey();
      }

      configureApi({
        baseUrl: getDefaultBaseUrl(),
        apiKey: normalizedKey,
      });

      let sovereign = !isTauri();
      if (isTauri()) {
        try {
          const bootstrapStatus = await getBootstrapStatus();
          sovereign = bootstrapStatus.sovereign_setup;
          if (sovereign) {
            await ensureApxvServerStarted();
            await waitForApiHealth(45_000);
          }
        } catch {
          // Bootstrap/setup screens surface status; don't block shell forever.
        }
      }

      setApiKeyState(normalizedKey);
      setOnboarded(complete);
      setSovereignReady(sovereign);
      router.update({ context: { onboarded: complete, sovereignReady: sovereign } });
      setReady(true);
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const setApiKey = useCallback(async (key: string) => {
    const normalized = normalizeOperatorApiKey(key);
    if (!normalized) {
      throw new Error(
        "Invalid API key. Paste the single line from OPERATOR-KEY-*.txt (letters, numbers, _ and - only).",
      );
    }
    await saveApiKey(normalized);
    configureApi({ apiKey: normalized });
    setApiKeyState(normalized);
  }, []);

  const completeOnboarding = useCallback(async () => {
    await setOnboardingComplete(true);
    setOnboarded(true);
  }, []);

  const resetOnboarding = useCallback(async () => {
    await clearApiKey();
    await setOnboardingComplete(false);
    configureApi({ apiKey: null });
    setApiKeyState(null);
    setOnboarded(false);
  }, []);

  /** Session expired (401) — keep API key, require re-validation only. */
  const invalidateSession = useCallback(async () => {
    await setOnboardingComplete(false);
    setOnboarded(false);
  }, []);

  const value = useMemo(
    () => ({
      ready,
      sovereignReady,
      apiKey,
      onboarded,
      setApiKey,
      completeOnboarding,
      resetOnboarding,
      invalidateSession,
    }),
    [
      ready,
      sovereignReady,
      apiKey,
      onboarded,
      setApiKey,
      completeOnboarding,
      resetOnboarding,
      invalidateSession,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

async function waitForApiHealth(timeoutMs: number): Promise<void> {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    try {
      await getSystemHealth();
      return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error("useApp must be used within AppProvider");
  }
  return ctx;
}