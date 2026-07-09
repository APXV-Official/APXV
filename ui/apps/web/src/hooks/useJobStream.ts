import { streamJobs, type Job, type JobStreamEvent } from "@apxv/api-client";
import { useEffect, useRef, useState } from "react";

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
          setConnected(true);
          setError(null);
          for await (const event of streamJobs({
            seconds: 60,
            pollMs: 1000,
            signal: controller.signal,
          })) {
            if (cancelled) break;
            jobsRef.current.set(event.job_id, event.job);
            setEvents((prev) => {
              const next = [...prev, event];
              return next.slice(-100);
            });
          }
        } catch (err) {
          if (controller.signal.aborted || cancelled) break;
          setError((err as Error).message);
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