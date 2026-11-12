"use client";

import { CircleHelp } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { TaxIcon } from "@/components/triage/icons";
import { DevTimer, useLabel, useTaxonomy } from "@/components/triage/shared";
import { inputCls } from "@/components/ui/field";
import { useTriage } from "@/lib/triage-store";
import { RecentReferrals } from "@/components/worker/referrals";

/** Start a walk-in: same emergency buttons as the patient app, on behalf of the person at the counter. */
export default function WorkerHome() {
  const router = useRouter();
  const label = useLabel();
  const { data: tax } = useTaxonomy();
  const { reset, begin, setLocation } = useTriage();
  const [phone, setPhone] = useState("");

  useEffect(() => {
    reset("worker");
    try {
      sessionStorage.removeItem("vitalis-timer");
    } catch {
      /* ignore */
    }
    // Optional: if GPS is refused the backend uses the shop's registered location.
    navigator.geolocation?.getCurrentPosition(
      (pos) => setLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => {},
      { timeout: 8000, maximumAge: 300000 },
    );
  }, [reset, setLocation]);

  const familyPhone = /^\+?[0-9 ]{7,20}$/.test(phone.trim()) ? phone.trim() : undefined;
  const start = (code: string | null, next: string) => {
    const step = next === "emergency" ? "emergency" : next === "who_child" ? "who_child" : next === "who" ? "who" : "body";
    void begin(code ? [{ kind: "emergency", code }] : [], step, { familyPhone });
    router.push("/worker/triage");
  };

  return (
    <main className="mx-auto w-full max-w-md space-y-4 px-4 py-4">
      <DevTimer />
      <section>
        <h1 className="text-2xl font-bold">New walk-in</h1>
        <p className="text-sm text-muted-foreground">
          Triage on behalf of the patient. They get a VITALIS ID and a recovery slip at the end.
        </p>
      </section>
      <label className="grid gap-1 text-sm font-medium">
        Family phone for alerts (optional)
        <input value={phone} onChange={(e) => setPhone(e.target.value)} type="tel" inputMode="tel"
          placeholder="+234…" className={inputCls} />
      </label>
      <div className="grid grid-cols-2 gap-2">
        {(tax?.emergencies ?? []).map((e) => (
          <button key={e.code} type="button" onClick={() => start(e.code, e.next)}
            className="flex min-h-24 flex-col items-center justify-center gap-1.5 rounded-2xl border-2 border-border bg-card p-2 text-center font-semibold leading-tight active:bg-mint">
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-emergency-soft text-emergency">
              <TaxIcon name={e.icon} className="h-6 w-6" />
            </span>
            {label(e.labels)}
          </button>
        ))}
      </div>
      <button type="button" onClick={() => start(null, "who")}
        className="flex min-h-16 w-full items-center justify-center gap-2 rounded-2xl bg-primary text-lg font-bold text-primary-foreground">
        <CircleHelp className="h-6 w-6" aria-hidden /> Something else
      </button>
      <section>
        <h2 className="mb-2 font-bold">Recent referrals</h2>
        <RecentReferrals limit={3} />
      </section>
    </main>
  );
}
