import { authHeaders, getApiConfig, notifyUnauthorized } from "./configure";
import type { Job } from "./jobs";

export interface JobStreamEvent {
  job_id: string;
  status: string;
  job: Job;
}

function parseSseChunk(buffer: string): {
  events: JobStreamEvent[];
  remainder: string;
} {
  const events: JobStreamEvent[] = [];
  const blocks = buffer.split("\n\n");
  const remainder = blocks.pop() ?? "";

  for (const block of blocks) {
    if (!block.trim()) continue;
    let eventType = "";
    let data = "";
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) eventType = line.slice(6).trim();
      if (line.startsWith("data:")) data = line.slice(5).trim();
    }
    if (eventType === "job" && data) {
      try {
        const parsed = JSON.parse(data) as JobStreamEvent;
        events.push(parsed);
      } catch {
        /* ignore malformed */
      }
    }
  }

  return { events, remainder };
}

export async function* streamJobs(options?: {
  seconds?: number;
  pollMs?: number;
  signal?: AbortSignal;
}): AsyncGenerator<JobStreamEvent> {
  const config = getApiConfig();
  const params = new URLSearchParams();
  if (options?.seconds) params.set("seconds", String(options.seconds));
  if (options?.pollMs) params.set("poll_ms", String(options.pollMs));

  const base = config.baseUrl.replace(/\/$/, "");
  const suffix = params.size ? `?${params}` : "";
  const headers: Record<string, string> = {
    Accept: "text/event-stream",
    ...authHeaders(config.apiKey),
  };

  const response = await fetch(`${base}/api/v2/jobs/stream${suffix}`, {
    headers,
    signal: options?.signal,
  });

  if (!response.ok || !response.body) {
    if (response.status === 401) notifyUnauthorized();
    throw new Error(`Job stream failed (${response.status})`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parsed = parseSseChunk(buffer);
    buffer = parsed.remainder;
    for (const event of parsed.events) {
      yield event;
    }
  }
}