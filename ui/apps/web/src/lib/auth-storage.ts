import { isTauri } from "./tauri";

export const API_KEY_STORAGE_KEY = "apxv.apiKey";
export const ONBOARDING_STORAGE_KEY = "apxv.onboardingComplete";

const API_KEY_KEY = API_KEY_STORAGE_KEY;
const ONBOARDING_KEY = ONBOARDING_STORAGE_KEY;

/** Synchronous read for router bootstrap (web localStorage only). */
export function readOnboardedSync(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(ONBOARDING_STORAGE_KEY) === "true";
}
const STORE_FILE = "apxv-settings.json";

async function getStore() {
  const { load } = await import("@tauri-apps/plugin-store");
  return load(STORE_FILE, { autoSave: true, defaults: {} });
}

export async function loadApiKey(): Promise<string | null> {
  if (isTauri()) {
    const store = await getStore();
    const value = await store.get<string>(API_KEY_KEY);
    return value ?? null;
  }
  return localStorage.getItem(API_KEY_KEY);
}

export async function saveApiKey(key: string): Promise<void> {
  if (isTauri()) {
    const store = await getStore();
    await store.set(API_KEY_KEY, key);
    await store.save();
    return;
  }
  localStorage.setItem(API_KEY_KEY, key);
}

export async function clearApiKey(): Promise<void> {
  if (isTauri()) {
    const store = await getStore();
    await store.delete(API_KEY_KEY);
    await store.save();
    return;
  }
  localStorage.removeItem(API_KEY_KEY);
}

export async function isOnboardingComplete(): Promise<boolean> {
  if (isTauri()) {
    const store = await getStore();
    return (await store.get<boolean>(ONBOARDING_KEY)) === true;
  }
  return localStorage.getItem(ONBOARDING_KEY) === "true";
}

export async function setOnboardingComplete(complete: boolean): Promise<void> {
  if (isTauri()) {
    const store = await getStore();
    await store.set(ONBOARDING_KEY, complete);
    await store.save();
    return;
  }
  if (complete) {
    localStorage.setItem(ONBOARDING_KEY, "true");
  } else {
    localStorage.removeItem(ONBOARDING_KEY);
  }
}