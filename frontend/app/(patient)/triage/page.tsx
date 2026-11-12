"use client";

import { ArrowRight, Phone, Siren } from "lucide-react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { BodyMap, type BodyView } from "@/components/body-map/BodyMap";
import { Face } from "@/components/triage/Faces";
import { ExcludedList, HospitalCardView } from "@/components/triage/HospitalList";
import { TaxIcon } from "@/components/triage/icons";
import { LocationPicker } from "@/components/triage/LocationPicker";
import {
  DevTimer,
  HospitalBar,
  StepHeader,
  useLabel,
  useTaxonomy,
  type Taxonomy,
} from "@/components/triage/shared";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, type ReferralPatientOut, type TriageOut } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useTriage } from "@/lib/triage-store";
import { cn } from "@/lib/utils";

const HospitalMap = dynamic(() => import("@/components/triage/HospitalMap"), { ssr: false });

function BigOption({
  onClick,
  icon,
  children,
  selected,
}: {
  onClick: () => void;
  icon?: React.ReactNode;
  children: React.ReactNode;
  selected?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={cn(
        "flex min-h-24 flex-col items-center justify-center gap-2 rounded-2xl border-2 p-3 text-center text-lg font-semibold leading-tight active:scale-[0.98]",
        selected ? "border-primary bg-mint" : "border-border bg-card",
      )}
    >
      {icon}
      {children}
    </button>
  );
}

export default function TriagePage() {
  const router = useRouter();
  const t = useT();
  const label = useLabel();
  const { data: tax } = useTaxonomy();
  const s = useTriage();
  const [view, setView] = useState<BodyView>("front");
  const [requesting, setRequesting] = useState<string | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);

  // Landing here without a started triage (e.g. reload) -> back home.
  useEffect(() => {
    if (!s.reportId && !s.busy) {
      const id = setTimeout(() => {
        if (!useTriage.getState().reportId && !useTriage.getState().busy) router.replace("/");
      }, 1500);
      return () => clearTimeout(id);
    }
  }, [s.reportId, s.busy, router]);

  const ctx = (s.result?.context ?? {}) as { age_group?: string; sex?: string; pregnant?: boolean };
  const regionLabels = useMemo(
    () => Object.fromEntries((tax?.regions ?? []).map((r) => [r.code, label(r.labels)])),
    [tax, label],
  );

  const tapAndGo = (taps: Parameters<typeof s.tap>[0], next: typeof s.step) => {
    s.countTap();
    if (taps.length) s.tap(taps);
    s.go(next);
  };

  const request = async (facilityId: string) => {
    s.countTap();
    setRequesting(facilityId);
    setRequestError(null);
    try {
      await s.flush();
      const ref = await api<ReferralPatientOut>(`/triage/${s.reportId}/referral`, {
        body: { facility_id: facilityId },
        patient: true,
      });
      router.push(`/referral/${ref.id}`);
    } catch (e) {
      setRequestError((e as Error).message);
      setRequesting(null);
    }
  };

  if (!tax) {
    return <main className="p-6 text-center text-muted-foreground">{t("common.loading")}</main>;
  }

  const content = (() => {
    switch (s.step) {
      case "emergency":
        return <EmergencyStep result={s.result} busy={s.busy} onRequest={request} requesting={requesting} />;
      case "who":
        return (
          <>
            <StepHeader title={t("who.title")} audio="who_title" onBack={() => router.push("/")} />
            <div className="grid grid-cols-2 gap-3">
              {tax.who.map((w) => (
                <BigOption
                  key={w.code}
                  icon={<TaxIcon name={w.icon} className="h-10 w-10 text-primary" />}
                  onClick={() =>
                    tapAndGo(
                      [{ kind: "context", ...(w.context as object), who: w.code }],
                      w.code === "child" ? "who_child" : w.code === "pregnant" ? "body" : "sex",
                    )
                  }
                >
                  {label(w.labels)}
                </BigOption>
              ))}
            </div>
          </>
        );
      case "who_child": {
        const child = tax.who.find((w) => w.code === "child");
        return (
          <>
            <StepHeader title={t("who.child_age")} audio="who_child_age" onBack={s.history.length ? s.back : undefined} />
            <div className="grid gap-3">
              {(child?.sub ?? []).map((w) => (
                <BigOption
                  key={w.code}
                  onClick={() => {
                    if (s.entry === "child_sick") {
                      s.countTap();
                      s.tap([{ kind: "context", ...(w.context as object) }]);
                      s.setRegion("whole_body");
                      s.go("symptoms");
                    } else {
                      tapAndGo([{ kind: "context", ...(w.context as object) }], "sex");
                    }
                  }}
                >
                  {label(w.labels)}
                </BigOption>
              ))}
            </div>
          </>
        );
      }
      case "sex":
        return (
          <>
            <StepHeader title={t("who.sex")} audio="who_sex" onBack={s.back} />
            <div className="grid grid-cols-2 gap-3">
              {(["female", "male"] as const).map((sex) => (
                <BigOption
                  key={sex}
                  icon={<span className="text-4xl text-primary">{sex === "female" ? "♀" : "♂"}</span>}
                  onClick={() => tapAndGo([{ kind: "context", sex }], "body")}
                >
                  {t(`sex.${sex}`)}
                </BigOption>
              ))}
            </div>
          </>
        );
      case "body":
        return (
          <>
            <StepHeader
              title={view === "head" ? t("body.zoom_head") : t("body.title")}
              audio="body_title"
              onBack={view === "head" ? () => setView("front") : s.history.length ? s.back : () => router.push("/")}
            />
            {view !== "head" ? (
              <div className="mb-2 grid grid-cols-2 gap-2 rounded-xl bg-muted p-1">
                {(["front", "back"] as const).map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => setView(v)}
                    className={cn("min-h-12 rounded-lg font-semibold", view === v && "bg-card shadow")}
                  >
                    {t(`body.${v}`)}
                  </button>
                ))}
              </div>
            ) : null}
            <BodyMap
              view={view}
              active={s.region}
              labels={regionLabels}
              onSelect={(region) => {
                if (region === "head" && view !== "head") {
                  setView("head");
                  return;
                }
                s.countTap();
                s.setRegion(region);
                s.go("symptoms");
              }}
            />
            <div className="mt-3 grid grid-cols-2 gap-2">
              {[
                ...(ctx.pregnant ? ["pelvis", "lower_abdomen"] : []),
                "whole_body",
                "skin",
              ].map((r) => (
                <Button
                  key={r}
                  variant={r === "whole_body" ? "primary" : "outline"}
                  size="lg"
                  className={r === "whole_body" ? "col-span-2" : ""}
                  onClick={() => {
                    s.countTap();
                    s.setRegion(r);
                    s.go("symptoms");
                  }}
                >
                  {r === "whole_body" ? t("body.whole") : regionLabels[r]}
                </Button>
              ))}
            </div>
          </>
        );
      case "symptoms":
        return (
          <SymptomsStep
            tax={tax}
            region={s.region}
            ctx={ctx}
            selected={s.selected}
            onToggle={(code) => {
              s.countTap();
              s.toggleSymptom(code, s.region);
            }}
            onBack={s.back}
            onMore={() => {
              setView("front");
              s.go("body");
            }}
            onNext={() => {
              s.countTap();
              s.go("severity");
            }}
          />
        );
      case "severity":
        return (
          <>
            <StepHeader title={t("severity.title")} audio="severity_title" onBack={s.back} />
            <div className="grid gap-2">
              {tax.severity.map((sv) => (
                <button
                  key={sv.value}
                  type="button"
                  onClick={() => tapAndGo([{ kind: "severity", value: sv.value }], "onset")}
                  className="flex min-h-20 items-center gap-4 rounded-2xl border-2 border-border bg-card px-4 text-left text-xl font-semibold active:bg-mint"
                >
                  <Face level={sv.value} size={60} />
                  {label(sv.labels)}
                </button>
              ))}
            </div>
          </>
        );
      case "onset":
        return (
          <>
            <StepHeader title={t("onset.title")} audio="onset_title" onBack={s.back} />
            <div className="grid grid-cols-2 gap-3">
              {tax.onset.map((o) => (
                <BigOption
                  key={o.code}
                  icon={<TaxIcon name={o.icon} className="h-10 w-10 text-primary" />}
                  onClick={() => {
                    tapAndGo([{ kind: "onset", value: o.code }], "results");
                    void s.flush();
                  }}
                >
                  {label(o.labels)}
                </BigOption>
              ))}
            </div>
          </>
        );
      case "results":
        return <ResultsStep result={s.result} onRequest={request} requesting={requesting} onBack={s.back} />;
    }
  })();

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col px-4">
      <DevTimer />
      <div className="flex-1 pb-2">{content}</div>
      {requestError ? <p className="py-2 text-center text-emergency">{requestError}</p> : null}
      {s.error ? <p className="py-2 text-center text-sm text-muted-foreground">{s.error}</p> : null}
      {s.step !== "emergency" && s.step !== "results" ? <HospitalBar result={s.result} busy={s.busy} /> : null}
    </main>
  );
}

function SymptomsStep({
  tax,
  region,
  ctx,
  selected,
  onToggle,
  onBack,
  onMore,
  onNext,
}: {
  tax: Taxonomy;
  region: string | null;
  ctx: { age_group?: string; sex?: string; pregnant?: boolean };
  selected: string[];
  onToggle: (code: string) => void;
  onBack: () => void;
  onMore: () => void;
  onNext: () => void;
}) {
  const t = useT();
  const label = useLabel();
  const isChild = ctx.age_group === "under5" || ctx.age_group === "child";
  const cards = tax.symptoms.filter(
    (sym) =>
      region &&
      sym.regions.includes(region) &&
      !sym.emergency_only &&
      (!sym.pregnant_only || ctx.pregnant) &&
      (!sym.female_only || ctx.sex === "female" || ctx.pregnant) &&
      (!sym.child_only || isChild),
  );
  // Seizure is a whole-body danger sign worth showing for children.
  const extra =
    region === "whole_body" && isChild ? tax.symptoms.filter((x) => x.code === "SEIZURE" || x.code === "UNCONSCIOUS") : [];
  const all = [...cards, ...extra.filter((e) => !cards.some((c) => c.code === e.code))];
  const regionName = label(tax.regions.find((r) => r.code === region)?.labels);
  return (
    <>
      <StepHeader title={t("symptoms.title")} audio="symptoms_title" onBack={onBack} />
      <p className="-mt-2 mb-3 text-muted-foreground">{regionName}</p>
      <div className="grid grid-cols-2 gap-3">
        {all.map((sym) => {
          const on = selected.includes(sym.code);
          return (
            <BigOption
              key={sym.code}
              selected={on}
              onClick={() => onToggle(sym.code)}
              icon={
                <TaxIcon
                  name={sym.icon}
                  className={cn("h-10 w-10", sym.icon.startsWith("bleeding") ? "text-emergency" : "text-primary")}
                />
              }
            >
              {label(sym.labels)}
            </BigOption>
          );
        })}
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3">
        <Button variant="outline" size="lg" onClick={onMore}>
          {t("symptoms.other_place")}
        </Button>
        <Button size="lg" onClick={onNext} disabled={!selected.length}>
          {t("symptoms.done")} <ArrowRight className="h-5 w-5" />
        </Button>
      </div>
    </>
  );
}

function EmergencyStep({
  result,
  busy,
  onRequest,
  requesting,
}: {
  result: TriageOut | null;
  busy: boolean;
  onRequest: (id: string) => void;
  requesting: string | null;
}) {
  const t = useT();
  const top = result?.hospitals.top ?? [];
  return (
    <div className="space-y-3 py-3">
      <div className="rounded-2xl bg-emergency p-4 text-white" role="alert">
        <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide">
          <Siren className="h-5 w-5" aria-hidden /> {t("emergency.title")}
        </div>
        <p className="mt-1 text-2xl font-bold leading-snug">
          {result?.red_flag.message ?? (busy ? t("common.loading") : t("results.go_now"))}
        </p>
      </div>
      <a
        href="tel:112"
        className="flex min-h-16 items-center justify-center gap-2 rounded-2xl border-2 border-emergency text-xl font-bold text-emergency"
      >
        <Phone className="h-6 w-6" aria-hidden /> {t("emergency.call")}
      </a>
      {result?.heads_up_sent ? (
        <p className="text-center text-sm text-muted-foreground">{t("emergency.heads_up")}</p>
      ) : null}
      {top.map((h, i) => (
        <HospitalCardView
          key={h.facility_id}
          h={h}
          primary={i === 0}
          emergency
          onRequest={() => onRequest(h.facility_id)}
          requesting={requesting === h.facility_id}
        />
      ))}
      {result && !top.length ? <Card className="text-center font-semibold">{t("referral.none")}</Card> : null}
      <LocationPicker />
      {result ? <ExcludedList result={result} /> : null}
    </div>
  );
}

const ACTION_KEY = {
  go_now: "results.go_now",
  go_today: "results.go_today",
  see_chemist: "results.see_chemist",
  self_care: "results.self_care",
} as const;

function ResultsStep({
  result,
  onRequest,
  requesting,
  onBack,
}: {
  result: TriageOut | null;
  onRequest: (id: string) => void;
  requesting: string | null;
  onBack: () => void;
}) {
  const t = useT();
  if (!result?.action_level) {
    return <p className="p-6 text-center text-muted-foreground">{t("common.loading")}</p>;
  }
  const title = t(ACTION_KEY[result.action_level]);
  const top = result.hospitals.top;
  return (
    <div className="space-y-3 pb-4">
      <StepHeader title={title} audio={`action_${result.action_level}`} onBack={onBack} />
      {result.action_level === "self_care" ? (
        <Card>
          <p className="font-semibold">{t("results.come_back_if")}</p>
          <ul className="mt-1 list-disc pl-5">
            {result.self_care_return_if.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </Card>
      ) : null}
      <LocationPicker />
      <h2 className="pt-1 text-lg font-bold">{t("results.best")}</h2>
      {top.length ? (
        <HospitalMap
          points={top.map((h, i) => ({ id: h.facility_id, name: h.name, lat: h.lat, lng: h.lng, highlight: i === 0 }))}
        />
      ) : null}
      {top.map((h, i) => (
        <HospitalCardView
          key={h.facility_id}
          h={h}
          primary={i === 0}
          onRequest={() => onRequest(h.facility_id)}
          requesting={requesting === h.facility_id}
        />
      ))}
      <ExcludedList result={result} />
    </div>
  );
}
