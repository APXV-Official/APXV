export const APXV_API_DEFAULT_BASE = "http://127.0.0.1:8741";
export const APXV_UI_VERSION = "1.3.0";
/** Production desktop data root placeholder (V1.3-PRODUCT-SPEC §3.1). Tauri resolves per OS at runtime. */
export const DEFAULT_APXV_ROOT = "%LOCALAPPDATA%\\APXV";

export type ConnectionState = "connected" | "degraded" | "unreachable";

export type OnboardingStep = "welcome" | "connect" | "doctor" | "complete";