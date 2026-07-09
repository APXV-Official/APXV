import { streamJobs, type Job, type JobStreamEvent } from "@apxv/api-client";
import { useEffect, useRef, useState } from "react";

function formatStreamError(err: unknown): string {
  const message = err instanceof Error ? err.message : "Stream unavailable";
  if (message === "Failed to fetch" || message === "Load failed") {
    return "Live stream blocked — using polling";
  }
  return message;
}

export function useJobStream(enabled = true) {
  const [events, setEvents] = useState<JobStreamEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const jobsRef = useRef<Map<string, Job>>(new Map());

  useEffect(() => {
    if (!enabled) return;

    const controller = new AbortController();
    let cancelled = false;

    async function connect() {
      while (!cancelled) {
        try {
          setConnected(false);
          setError(null);
          for await (const event of streamJobs({
            seconds: 60,
            pollMs: 1000,
            signal: controller.signal,
          })) {
            if (cancelled) break;
            setConnected(true);
            jobsRef.current.set(event.job_id, event.job);
            setEvents((prev) => {
              const next = [...prev, event];
              return next.slice(-100);
            });
          }
          if (!cancelled) {
            setConnected(false);
          }
        } catch (err) {
          if (controller.signal.aborted || cancelled) break;
          setError(formatStreamError(err));
          setConnected(false);
          await new Promise((r) => setTimeout(r, 3000));
        }
      }
    }

    void connect();
    return () => {
      cancelled = true;
      controller.abort();
      setConnected(false);
    };
  }, [enabled]);

  return { events, connected, error, jobs: jobsRef.current };
}