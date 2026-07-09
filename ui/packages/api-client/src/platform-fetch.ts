type FetchFn = typeof fetch;

let cachedFetch: FetchFn | null | undefined;

function isTauriRuntime(): boolean {
  return (
    typeof window !== "undefined" &&
    ("__TAURI_INTERNALS__" in window || "__TAURI__" in window)
  );
}

/**
 * Desktop webviews load the UI over HTTPS (tauri.localhost) while the API is
 * HTTP on 127.0.0.1:8741. WebKitGTK on Linux blocks that mixed-content fetch
 * ("Load failed"); Windows works only because WebView2 has an extra flag in
 * lib.rs. Tauri's HTTP plugin bypasses the webview network stack.
 */
export async function resolveFetch(): Promise<FetchFn> {
  if (cachedFetch !== undefined) {
    return cachedFetch ?? fetch;
  }

  if (!isTauriRuntime()) {
    cachedFetch = null;
    return fetch;
  }

  try {
    const { fetch: tauriFetch } = await import("@tauri-apps/plugin-http");
    cachedFetch = tauriFetch;
    return tauriFetch;
  } catch {
    cachedFetch = null;
    return fetch;
  }
}

/** Reset cached resolver (tests only). */
export function resetPlatformFetchCache(): void {
  cachedFetch = undefined;
}