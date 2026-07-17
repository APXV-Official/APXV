import { getSystemHealth } from "@apxv/api-client";

/** Poll local API health until responsive or timeout. */
export async function waitForHealth(timeoutMs: number): Promise<void> {
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