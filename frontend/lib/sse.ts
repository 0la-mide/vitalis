"use client";

import { getDeviceKey } from "@/lib/patient-store";

export type SseEvent = { event: string; data: unknown };

/**
 * Server-Sent Events over fetch (so patient requests can carry X-Patient-Key, which EventSource cannot).
 * Reconnects with backoff. Returns a stop function.
 */
export function subscribe(
  path: string,
  onEvent: (e: SseEvent) => void,
  opts: { patient?: boolean } = {},
): () => void {
  let stopped = false;
  let ctrl: AbortController | null = null;
  let backoff = 1000;
  let refreshed = false;

  const run = async () => {
    while (!stopped) {
      ctrl = new AbortController();
      try {
        const headers: Record<string, string> = { Accept: "text/event-stream" };
        if (opts.patient) {
          const key = await getDeviceKey();
          if (key) headers["X-Patient-Key"] = key;
        }
        const res = await fetch(`/api/v1${path}`, { headers, signal: ctrl.signal, credentials: "same-origin" });
        // Staff access tokens are short-lived: refresh once, then reconnect.
        if (res.status === 401 && !opts.patient && !refreshed) {
          refreshed = true;
          const csrf = document.cookie.match(/(?:^|; )vt_csrf=([^;]*)/)?.[1];
          const r = await fetch("/api/v1/auth/refresh", {
            method: "POST",
            credentials: "same-origin",
            headers: csrf ? { "X-CSRF-Token": decodeURIComponent(csrf) } : {},
          });
          if (r.ok) continue;
        }
        // Auth or not-found errors will not fix themselves: stop instead of hammering the server.
        if (res.status >= 400 && res.status < 500) {
          onEvent({ event: "error", data: { status: res.status } });
          return;
        }
        if (!res.ok || !res.body) throw new Error(`SSE ${res.status}`);
        backoff = 1000;
        refreshed = false;
        const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
        let buf = "";
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += value.replace(/\r\n/g, "\n");
          let idx;
          while ((idx = buf.indexOf("\n\n")) >= 0) {
            const block = buf.slice(0, idx);
            buf = buf.slice(idx + 2);
            let event = "message";
            const data: string[] = [];
            for (const line of block.split("\n")) {
              if (line.startsWith("event:")) event = line.slice(6).trim();
              else if (line.startsWith("data:")) data.push(line.slice(5).trim());
            }
            if (event === "ping") continue;
            let parsed: unknown = data.join("\n");
            try {
              parsed = JSON.parse(parsed as string);
            } catch {
              /* keep raw */
            }
            onEvent({ event, data: parsed });
          }
        }
      } catch {
        if (stopped) return;
      }
      if (stopped) return;
      await new Promise((r) => setTimeout(r, backoff));
      backoff = Math.min(backoff * 2, 10000);
    }
  };
  run();
  return () => {
    stopped = true;
    ctrl?.abort();
  };
}
