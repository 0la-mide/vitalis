"use client";

import { CircleHelp } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { TaxIcon } from "@/components/triage/icons";
import { DevTimer, LangPicker, SpeakButton, useLabel, useTaxonomy } from "@/components/triage/shared";
import { useT } from "@/lib/i18n";
import { useTriage } from "@/lib/triage-store";
import { Logo } from "@/components/staff/StaffShell";

export default function Home() {
  const t = useT();
  const label = useLabel();
  const router = useRouter();
  const { data: tax } = useTaxonomy();
  const { reset, begin, setLocation } = useTriage();

  useEffect(() => {
    reset();
    try {
      sessionStorage.removeItem("vitalis-timer");
    } catch {
      /* ignore */
    }
    // Ask for location early so it is ready by the first tap. Refusal is fine: we fall back to an area list.
    navigator.geolocation?.getCurrentPosition(
      (pos) => setLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => {},
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 300000 },
    );
  }, [reset, setLocation]);

  const startEmergency = (code: string, next: string, context?: Record<string, unknown>) => {
    const step = next === "emergency" ? "emergency" : next === "who_child" ? "who_child" : "body";
    void begin([{ kind: "emergency", code }], step, { context });
    router.push("/triage");
  };

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col px-4 pb-6">
      <DevTimer />
      <header className="flex items-center justify-between py-4">
        <Logo subtitle={t("app.tagline")} />
        <LangPicker />
      </header>

      <div className="flex items-center gap-3 pb-3">
        <h1 className="flex-1 text-3xl font-bold leading-tight">{t("home.title")}</h1>
        <SpeakButton code="home_title" text={t("home.title")} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        {(tax?.emergencies ?? []).map((e) => (
          <button
            key={e.code}
            type="button"
            onClick={() => startEmergency(e.code, e.next, e.context as Record<string, unknown>)}
            className="flex min-h-32 flex-col items-center justify-center gap-2 rounded-2xl border-2 border-border bg-card p-3 text-center text-lg font-semibold leading-tight shadow-sm active:scale-[0.98] active:bg-mint"
          >
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-calm-soft text-calm">
              <TaxIcon name={e.icon} className="h-8 w-8" />
            </span>
            {label(e.labels)}
          </button>
        ))}
        {!tax
          ? Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="min-h-32 animate-pulse rounded-2xl bg-muted" />
            ))
          : null}
      </div>

      <button
        type="button"
        onClick={() => {
          void begin([], "who");
          router.push("/triage");
        }}
        className="mt-3 flex min-h-20 items-center justify-center gap-3 rounded-2xl bg-primary px-4 text-xl font-bold text-primary-foreground active:bg-primary-strong"
      >
        <CircleHelp className="h-8 w-8" aria-hidden />
        {t("home.something_else")}
      </button>

      <a
        href="tel:112"
        className="mt-3 flex min-h-14 items-center justify-center rounded-2xl border-2 border-emergency text-lg font-bold text-emergency"
      >
        {t("emergency.call")}
      </a>

      <footer className="mt-auto flex justify-between pt-6 text-sm text-muted-foreground">
        <Link href="/card" className="underline-offset-4 hover:underline">
          {t("home.my_records")}
        </Link>
        <Link href="/auth/login" className="underline-offset-4 hover:underline">
          {t("home.staff")}
        </Link>
      </footer>
    </main>
  );
}
