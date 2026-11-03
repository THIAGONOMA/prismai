"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { apiUrl } from "@/lib/api/client";

interface JobEvent {
  type: string;
  job_id: string;
  progress: number;
  total: number;
}

interface UseJobStreamReturn {
  progress: number;
  total: number;
  done: boolean;
  error: string | null;
}

export function useJobStream(jobId: string | null): UseJobStreamReturn {
  const [progress, setProgress] = useState(0);
  const [total, setTotal] = useState(0);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const cleanup = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = null;
  }, []);

  useEffect(() => {
    if (!jobId) return;
    setProgress(0);
    setTotal(0);
    setDone(false);
    setError(null);

    const url = apiUrl(`/v1/jobs/${jobId}/events`);
    const es = new EventSource(url);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const data: JobEvent = JSON.parse(e.data);
        if (data.progress !== undefined) setProgress(data.progress);
        if (data.total !== undefined) setTotal(data.total);
        if (data.type === "done") {
          setDone(true);
          cleanup();
        }
      } catch { /* ignore parse errors */ }
    };

    es.onerror = () => {
      es.close();
      esRef.current = null;
      pollRef.current = setInterval(async () => {
        try {
          const res = await fetch(apiUrl(`/v1/jobs/${jobId}`));
          if (!res.ok) return;
          const data = await res.json();
          setProgress(data.progress ?? 0);
          setTotal(data.total ?? 0);
          if (data.status === "completed" || data.status === "failed") {
            setDone(true);
            if (data.status === "failed") setError("Job failed");
            cleanup();
          }
        } catch { /* ignore poll errors */ }
      }, 2000);
    };

    return cleanup;
  }, [jobId, cleanup]);

  return { progress, total, done, error };
}
