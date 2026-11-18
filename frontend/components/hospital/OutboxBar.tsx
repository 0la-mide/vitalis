"use client";

import { useQueryClient } from "@tanstack/react-query";
import { CloudOff, CloudUpload, TriangleAlert, X } from "lucide-react";
import { useEffect, useSyncExternalStore } from "react";
import { dismissFailed, flushOutbox, getSnapshot, subscribe } from "@/lib/outbox";

const EMPTY = { items: [], failed: [], online: true, sending: false };

/** Staff screens: says when the phone is offline, what is waiting to be sent, and what could not be sent. */
export function OutboxBar() {
  const qc = useQueryClient();
  const s = useSyncExternalStore(subscribe, getSnapshot, () => EMPTY);

  useEffect(() => {
    const refresh = () => void qc.invalidateQueries();
    const go = () => void flushOutbox(refresh);
    window.addEventListener("online", go);
    window.addEventListener("offline", go);
    const every = window.setInterval(go, 20000);
    go();
    return () => {
      window.removeEventListener("online", go);
      window.removeEventListener("offline", go);
      window.clearInterval(every);
    };
  }, [qc]);

  if (s.online && !s.items.length && !s.failed.length) return null;
  return (
    <div className="space-y-2 px-4 pt-3 lg:px-8">
      {!s.online || s.items.length ? (
        <div className="flex items-start gap-2 rounded-lg bg-warning-soft px-3 py-2 text-sm" role="status">
          {s.online ? <CloudUpload className="mt-0.5 h-4 w-4 shrink-0" /> : <CloudOff className="mt-0.5 h-4 w-4 shrink-0" />}
          <div>
            <b>{s.online ? (s.sending ? "Sending saved actions…" : "Back online") : "No signal"}</b>
            {s.items.length ? (
              <> · {s.items.length} saved on this phone, sent automatically when the signal returns:{" "}
                {s.items.map((i) => i.label).join(", ")}</>
            ) : (
              <> · You can keep working: accept, arrival and vitals are saved and sent when the signal returns.</>
            )}
          </div>
        </div>
      ) : null}
      {s.failed.length ? (
        <div className="flex items-start gap-2 rounded-lg bg-emergency-soft px-3 py-2 text-sm text-emergency" role="alert">
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
          <div className="flex-1">
            <b>Not sent:</b> {s.failed.map((f) => `${f.label} (${f.reason})`).join("; ")}
          </div>
          <button type="button" aria-label="Dismiss" onClick={dismissFailed}><X className="h-4 w-4" /></button>
        </div>
      ) : null}
    </div>
  );
}
