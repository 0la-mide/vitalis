"use client";

import { Activity, ChevronDown, UserRound } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { api, type TriageOut } from "@/lib/api";
import { useTriage } from "@/lib/triage-store";
import { VITAL_FIELDS } from "@/lib/vitals";
import { cn, timeAgo } from "@/lib/utils";

const FIELDS = VITAL_FIELDS;

type Saved = { kind: string; value: number; at: string };

/** "On behalf of patient" bar for frontline workers, with the vitals form. Vitals re-run the red-flag rules. */
export function WalkInBar({ vitalsOpen }: { vitalsOpen?: boolean }) {
  const walkIn = useTriage((s) => s.walkIn);
  const reportId = useTriage((s) => s.reportId);
  const setResult = useTriage((s) => s.setResult);
  const [toggled, setToggled] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<Saved[]>([]);
  const open = toggled ?? !!vitalsOpen;

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!walkIn || !reportId) return;
    const form = e.currentTarget;
    const fd = new FormData(form);
    const readings = FIELDS.flatMap((f) => {
      const raw = String(fd.get(f.kind) ?? "").trim();
      return raw ? [{ kind: f.kind, value: Number(raw) }] : [];
    });
    if (!readings.length) return;
    setBusy(true);
    setError(null);
    try {
      const out = await api<TriageOut>(`/worker/patients/${walkIn.patientId}/vitals`, {
        body: { report_id: reportId, readings },
      });
      const at = new Date().toISOString();
      setSaved((prev) => [...readings.map((r) => ({ ...r, at })), ...prev]);
      form.reset();
      setResult(out);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={cn("-mx-4 mb-2 border-b border-border bg-card/95 px-4 py-2 backdrop-blur",
      !open && "sticky top-0 z-30")}>
      <div className="flex items-center gap-2">
        <UserRound className="h-5 w-5 text-primary" aria-hidden />
        <div className="min-w-0 flex-1 text-sm">
          <div className="font-semibold">On behalf of patient</div>
          <div className="font-mono text-xs text-muted-foreground">{walkIn?.vitalisId ?? "creating…"}</div>
        </div>
        <Button size="sm" variant={open ? "mint" : "outline"} onClick={() => setToggled(!open)} disabled={!walkIn}
          aria-expanded={open}>
          <Activity className="h-4 w-4" /> Vitals{saved.length ? ` (${saved.length})` : ""}
          <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
        </Button>
      </div>
      {open && walkIn ? (
        <form onSubmit={submit} className="mt-2 space-y-2 pb-1">
          <div className="grid grid-cols-2 gap-2">
            {FIELDS.map((f) => (
              <label key={f.kind} className="grid min-w-0 gap-0.5 text-xs font-medium">
                <span>{f.label} <span className="font-normal text-muted-foreground">({f.unit})</span></span>
                <input name={f.kind} type="number" inputMode="decimal" step={f.step}
                  className="h-11 w-full min-w-0 rounded-lg border border-border bg-card px-2 text-base" />
              </label>
            ))}
          </div>
          {error ? <p className="text-sm text-emergency">{error}</p> : null}
          <Button type="submit" className="w-full" disabled={busy}>{busy ? "Saving…" : "Save vitals"}</Button>
          {saved.length ? (
            <ul className="flex flex-wrap gap-1.5 text-xs">
              {saved.map((v, i) => (
                <li key={i} className="rounded-md bg-muted px-2 py-1">
                  {FIELDS.find((f) => f.kind === v.kind)?.label} {v.value} · {timeAgo(v.at)}
                </li>
              ))}
            </ul>
          ) : null}
        </form>
      ) : null}
    </div>
  );
}
