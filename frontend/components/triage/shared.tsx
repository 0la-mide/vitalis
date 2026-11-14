"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, Languages, MapPin, Volume2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/card";
import { api, type HospitalCard, type Schemas, type TriageOut } from "@/lib/api";
import { speak } from "@/lib/audio";
import { LANGS, pickLabel, useActiveLang, useLang, useT, type Lang } from "@/lib/i18n";
import { cn, timeAgo } from "@/lib/utils";

export type Taxonomy = Schemas["Taxonomy"];

export function useTaxonomy() {
  return useQuery({
    queryKey: ["taxonomy"],
    queryFn: () => api<Taxonomy>("/triage/taxonomy"),
    staleTime: Infinity,
  });
}

export function useLabel() {
  const lang = useActiveLang();
  return (labels: Record<string, string> | undefined) => pickLabel(labels, lang);
}

export function SpeakButton({ code, text, className }: { code: string; text: string; className?: string }) {
  const lang = useActiveLang();
  const t = useT();
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        void speak(code, text, lang);
      }}
      className={cn(
        "inline-flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-mint text-primary-strong",
        className,
      )}
      aria-label={`${t("common.listen")}: ${text}`}
    >
      <Volume2 className="h-6 w-6" />
    </button>
  );
}

export function LangPicker() {
  const { lang, setLang } = useLang();
  return (
    <label className="inline-flex items-center gap-1 rounded-full bg-muted px-3 py-2 text-sm font-medium">
      <Languages className="h-4 w-4" aria-hidden />
      <span className="sr-only">Language</span>
      <select
        value={LANGS.find((l) => l.code === lang)?.ready ? lang : "en"}
        onChange={(e) => setLang(e.target.value as Lang)}
        className="w-[4.5rem] bg-transparent outline-none"
        suppressHydrationWarning
      >
        {LANGS.map((l) => (
          <option key={l.code} value={l.code} disabled={!l.ready}>
            {l.ready ? l.label : `${l.label} (coming soon)`}
          </option>
        ))}
      </select>
    </label>
  );
}

export function StepHeader({
  title,
  audio,
  onBack,
}: {
  title: string;
  audio: string;
  onBack?: () => void;
}) {
  const t = useT();
  return (
    <div className="flex items-center gap-3 py-3">
      {onBack ? (
        <button
          type="button"
          onClick={onBack}
          className="inline-flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-muted"
          aria-label={t("common.back")}
        >
          <ChevronLeft className="h-7 w-7" />
        </button>
      ) : null}
      <h1 className="flex-1 text-2xl font-bold leading-tight">{title}</h1>
      <SpeakButton code={audio} text={title} />
    </div>
  );
}

export function FreshnessBadge({ f, at }: { f: HospitalCard["freshness"]; at?: string | null }) {
  const t = useT();
  const tone = f === "confirmed" ? "ok" : f === "stale" ? "warn" : "neutral";
  return (
    <Badge tone={tone} title={at ? new Date(at).toLocaleString() : undefined}>
      {t(`fresh.${f}`)}
      {at ? ` · ${timeAgo(at)}` : ""}
    </Badge>
  );
}

/** Sticky live bar: suitable hospitals narrowing down on every tap. */
export function HospitalBar({ result, busy }: { result: TriageOut | null; busy?: boolean }) {
  const t = useT();
  if (!result) return null;
  const h = result.hospitals;
  const top = h.top[0];
  return (
    <div className="sticky bottom-0 z-20 -mx-4 mt-4 border-t border-border bg-card/95 px-4 py-3 backdrop-blur">
      <div className="flex items-center gap-2 text-sm" aria-live="polite">
        <span className={cn("h-2.5 w-2.5 rounded-full bg-primary", busy && "vt-pulse")} aria-hidden />
        <span>
          <b>{h.nearby}</b> {t("bar.nearby")} · <b>{h.can_handle}</b> {t("bar.can_handle")} ·{" "}
          <b>{h.ready_now}</b> {t("bar.ready")}
        </span>
      </div>
      {top ? (
        <div className="mt-1 truncate text-sm text-muted-foreground">
          {top.name} · {top.distance_km} {t("hospital.km")} · ~{top.eta_minutes} {t("hospital.minutes")}
        </div>
      ) : null}
      {h.approximate_location ? (
        <div className="mt-1 inline-flex items-center gap-1 text-xs text-muted-foreground">
          <MapPin className="h-3 w-3" aria-hidden /> {t("bar.approx")}
        </div>
      ) : null}
    </div>
  );
}

/** Dev-only: taps and seconds since the first tap, to measure the <=5 taps / <=15 s target. */
export function DevTimer() {
  const [state, setState] = useState<{ startedAt: number | null; taps: number; stoppedAt?: number }>({
    startedAt: null,
    taps: 0,
  });
  const [now, setNow] = useState(0);
  useEffect(() => {
    // Only when measuring: open the app with ?timer=1 (remembered for this tab).
    try {
      if (location.search.includes("timer=1")) sessionStorage.setItem("vitalis-show-timer", "1");
      if (!sessionStorage.getItem("vitalis-show-timer")) return;
    } catch {
      return;
    }
    const read = () => {
      try {
        const raw = sessionStorage.getItem("vitalis-timer");
        if (raw) setState(JSON.parse(raw));
      } catch {
        /* ignore */
      }
    };
    read();
    const id = setInterval(() => {
      read();
      setNow(Date.now());
    }, 250);
    return () => clearInterval(id);
  }, []);
  if (!state.startedAt || !now) return null;
  const end = state.stoppedAt ?? now;
  const secs = ((end - state.startedAt) / 1000).toFixed(1);
  return (
    <div className="pointer-events-none fixed bottom-24 right-2 z-50 rounded-lg bg-black/75 px-2 py-1 font-mono text-xs text-white">
      {state.taps} taps · {secs}s{state.stoppedAt ? " ✓" : ""}
    </div>
  );
}

export function stopDevTimer() {
  try {
    const raw = sessionStorage.getItem("vitalis-timer");
    if (!raw) return;
    const s = JSON.parse(raw);
    if (!s.stoppedAt) sessionStorage.setItem("vitalis-timer", JSON.stringify({ ...s, stoppedAt: Date.now() }));
  } catch {
    /* ignore */
  }
}

export function bumpDevTapCount() {
  try {
    const raw = sessionStorage.getItem("vitalis-timer");
    if (!raw) return;
    const s = JSON.parse(raw);
    sessionStorage.setItem("vitalis-timer", JSON.stringify({ ...s, taps: (s.taps ?? 0) + 1 }));
  } catch {
    /* ignore */
  }
}
