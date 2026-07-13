import { streamJobs, type JobStreamEvent } from "@apxv/api-client";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { patchJobsFromStreamEvent } from "../lib/jobs-cache";

function formatStreamError(err: unknown): string {
  const message = err instanceof Error ? err.message : "Stream unavailable";
  if (message === "Failed to fetch" || message === "Load failed") {
    return "Live stream blocked — using polling";
  }
  return message;
}

const BACKOFF_MS = [1000, 2000, 4000, 8000, 10_000];

export function useJobStream(enabled = true) {
  const queryClient = useQueryClient();
  const [events, setEvents] = useState<JobStreamEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const attemptRef = useRef(0);

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
            seconds: 120,
            pollMs: 500,
            signal: controller.signal,
          })) {
            if (cancelled) break;
            attemptRef.current = 0;
            setConnected(true);
            patchJobsFromStreamEvent(queryClient, event);
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
          const delay =
            BACKOFF_MS[Math.min(attemptRef.current, BACKOFF_MS.length - 1)];
          attemptRef.current += 1;
          await new Promise((r) => setTimeout(r, delay));
        }
      }
    }

    void connect();
    return () => {
      cancelled = true;
      controller.abort();
      setConnected(false);
    };
  }, [enabled, queryClient]);

  return { events, connected, error, lastEvent: events[events.length - 1] };
}