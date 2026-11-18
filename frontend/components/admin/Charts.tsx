"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export type Series = { key: string; label: string; color: string };
export type DayValues = { date: string; [k: string]: number | string };

const short = (iso: string) => new Date(`${iso}T12:00:00`).toLocaleDateString([], { day: "numeric", month: "short" });
const nice = (n: number) => {
  if (n <= 5) return 5;
  const p = 10 ** Math.floor(Math.log10(n));
  return [1, 2, 2.5, 5, 10].map((m) => m * p).find((v) => v >= n) ?? n;
};

/** Stacked bars per day. Legend with totals, hover for the day's numbers, and a table view. */
export function DailyBars({ title, rows, series, height = 180 }: {
  title: string; rows: DayValues[]; series: Series[]; height?: number;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const [table, setTable] = useState(false);
  const total = (r: DayValues) => series.reduce((a, s) => a + Number(r[s.key] ?? 0), 0);
  const max = nice(Math.max(1, ...rows.map(total)));
  const sums = Object.fromEntries(series.map((s) => [s.key, rows.reduce((a, r) => a + Number(r[s.key] ?? 0), 0)]));
  const h = hover != null ? rows[hover] : null;

  return (
    <Card className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h2 className="font-semibold">{title}</h2>
        <button type="button" onClick={() => setTable((t) => !t)} className="text-xs text-muted-foreground underline underline-offset-2">
          {table ? "Show chart" : "Show table"}
        </button>
      </div>
      {series.length > 1 ? (
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
          {series.map((s) => (
            <li key={s.key} className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ background: s.color }} aria-hidden />
              {s.label} <span className="tabular-nums text-muted-foreground">{sums[s.key]}</span>
            </li>
          ))}
        </ul>
      ) : null}

      {table ? (
        <div className="max-h-72 overflow-auto">
          <table className="w-full text-sm tabular-nums">
            <thead className="sticky top-0 bg-card text-left text-xs text-muted-foreground">
              <tr><th className="py-1">Day</th>{series.map((s) => <th key={s.key} className="py-1 text-right">{s.label}</th>)}</tr>
            </thead>
            <tbody>
              {[...rows].reverse().map((r) => (
                <tr key={r.date} className="border-t border-border">
                  <td className="py-1">{short(String(r.date))}</td>
                  {series.map((s) => <td key={s.key} className="py-1 text-right">{Number(r[s.key] ?? 0)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="relative" onMouseLeave={() => setHover(null)}>
          <div className="relative flex items-end gap-[2px] border-b border-border" style={{ height }}>
            {/* recessive grid: top and middle */}
            <div className="pointer-events-none absolute inset-x-0 top-0 border-t border-dashed border-border" aria-hidden />
            <div className="pointer-events-none absolute inset-x-0 border-t border-dashed border-border/60" style={{ top: height / 2 }} aria-hidden />
            <span className="pointer-events-none absolute -top-2 right-0 bg-card pl-1 text-[10px] text-muted-foreground">{max}</span>
            {rows.map((r, i) => {
              const t = total(r);
              return (
                <div
                  key={r.date}
                  className={cn("relative flex h-full flex-1 cursor-default flex-col justify-end", hover === i && "bg-muted/60")}
                  onMouseEnter={() => setHover(i)}
                  onFocus={() => setHover(i)}
                  tabIndex={0}
                  aria-label={`${short(String(r.date))}: ${series.map((s) => `${s.label} ${Number(r[s.key] ?? 0)}`).join(", ")}`}
                >
                  <div className="flex flex-col-reverse gap-[2px]" style={{ height: `${(t / max) * 100}%` }}>
                    {series.map((s, k) => {
                      const v = Number(r[s.key] ?? 0);
                      if (!v) return null;
                      const top = series.slice(k + 1).every((x) => !Number(r[x.key] ?? 0));
                      return (
                        <div key={s.key} style={{ flexGrow: v, background: s.color }}
                          className={cn("min-h-[2px] w-full", top && "rounded-t-[4px]")} />
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
            <span>{rows[0] ? short(String(rows[0].date)) : ""}</span>
            <span>{rows.at(-1) ? short(String(rows.at(-1)!.date)) : ""}</span>
          </div>
          {h ? (
            <div
              className="pointer-events-none absolute -top-2 z-10 min-w-36 -translate-y-full rounded-lg border border-border bg-card px-3 py-2 text-xs shadow-lg"
              style={{ left: `clamp(0px, calc(${((hover! + 0.5) / rows.length) * 100}% - 72px), calc(100% - 150px))` }}
            >
              <p className="font-semibold">{short(String(h.date))}</p>
              {series.map((s) => (
                <p key={s.key} className="flex items-center justify-between gap-3">
                  <span className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-sm" style={{ background: s.color }} aria-hidden />{s.label}
                  </span>
                  <span className="tabular-nums">{Number(h[s.key] ?? 0)}</span>
                </p>
              ))}
            </div>
          ) : null}
        </div>
      )}
    </Card>
  );
}

/** One series, horizontal bars with the value beside each: breakdowns and funnels. */
export function HBars({ title, items, note }: { title: string; items: { label: string; value: number }[]; note?: string }) {
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <Card className="space-y-3">
      <h2 className="font-semibold">{title}</h2>
      <ul className="space-y-2">
        {items.map((i) => (
          <li key={i.label} className="grid grid-cols-[minmax(7rem,10rem)_1fr_3rem] items-center gap-2 text-sm" title={`${i.label}: ${i.value}`}>
            <span className="truncate">{i.label}</span>
            <span className="h-3 rounded-r-[4px] bg-[var(--series-1)]" style={{ width: `${Math.max(i.value ? 2 : 0, (i.value / max) * 100)}%` }} />
            <span className="text-right tabular-nums">{i.value}</span>
          </li>
        ))}
        {!items.length ? <li className="text-sm text-muted-foreground">Nothing yet.</li> : null}
      </ul>
      {note ? <p className="text-xs text-muted-foreground">{note}</p> : null}
    </Card>
  );
}

export function Stat({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <Card className="h-full">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="mt-1 text-3xl font-bold tabular-nums">{value}</div>
      {sub ? <div className="mt-1 text-xs text-muted-foreground">{sub}</div> : null}
    </Card>
  );
}

export const ROLE_LABEL: Record<string, string> = {
  network_admin: "Network admin", facility_admin: "Hospital admin", receptionist: "Reception", nurse: "Nurse",
  doctor: "Doctor", lab: "Lab", radiology: "Radiology", worker: "Chemist / frontline",
};
