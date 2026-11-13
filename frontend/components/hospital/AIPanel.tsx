"use client";

/**
 * VITALIS AI panel, ported from the team's NCS frontend (AIAssessment.tsx) to this app.
 * The engine output shape is defined by backend/app/engines/clinical/assessment.py (Assessment.run).
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertOctagon, BookOpen, BrainCircuit, Check, CheckCircle2, ChevronDown, CircleSlash, Cpu, FlaskConical, History,
  Info, Plus, ShieldAlert, Sparkles, TrendingUp, TriangleAlert, Users, X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/card";
import { inputCls } from "@/components/ui/field";
import { api, type Schemas } from "@/lib/api";
import { cn } from "@/lib/utils";

type Evidence = { text: string; source: string; kind: "current" | "history" | "lab" | "family" | "ml" | "rule" };
type Condition = {
  key: string; rank: number; condition: string; likelihood: number; likelihood_label: string;
  evidence: Evidence[]; against: Evidence[]; recommended_investigations: string[];
  management_considerations: string[]; guideline: string;
};
type ModelRun = {
  key: string; name: string; algorithm: string; model_version: string; band: string; probability: number; note: string;
  inputs: { feature: string; label: string; value: number; source: string; detail: string }[];
  measured_inputs: number; total_inputs: number;
};
export type AIOutput = {
  engine_version: string; summary: string; analysis_trace: string[]; safety_disclaimer: string;
  data_coverage: { prior_visits: number; facilities: string[]; vital_readings: number; lab_values: number };
  red_flags: { severity: string; title: string; detail: string; action: string }[];
  conditions: Condition[];
  trends: { metric: string; text: string; direction: string }[];
  ml_models: ModelRun[];
  medication_options: { drug: string; for_condition: string; rationale: string; safety: "ok" | "caution" | "avoid"; alerts: string[] }[];
  missing_data: string[];
  narrative: { provider: string; summary: string };
};
type Draft = Omit<Schemas["DraftOut"], "output"> & { output: AIOutput };

const PRE_STEPS = ["Reading today's visit, vitals and the referral", "Loading earlier visits and lab results",
  "Checking allergies and medicines recorded across the network"];

/** AI test suggestions → this hospital's test catalogue. */
const TEST_CODES: [RegExp, string][] = [
  [/hba1c/i, "HBA1C"], [/fasting/i, "FBS"], [/lipid/i, "LIPIDS"], [/full blood count/i, "FBC"], [/malaria rdt/i, "MP_RDT"],
  [/blood film/i, "MP_FILM"], [/urinalysis/i, "URINALYSIS"], [/creatinine|electrolytes/i, "E_U_CR"], [/\becg\b/i, "ECG"],
  [/chest x-ray/i, "CXR"],
];

export function AIPanel({ encounterId, canOrder, onOrdered }: { encounterId: string; canOrder: boolean; onOrdered: () => void }) {
  const qc = useQueryClient();
  const key = ["ai-draft", encounterId];
  const { data: latest } = useQuery({ queryKey: key, queryFn: () => api<Draft | null>(`/hospital/encounters/${encounterId}/ai-draft`) });
  const [phase, setPhase] = useState<"idle" | "running" | "revealing">("idle");
  const [steps, setSteps] = useState<string[]>([]);
  const [shown, setShown] = useState(0);
  const [pending, setPending] = useState<Draft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const root = useRef<HTMLDivElement>(null);

  const run = async () => {
    root.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    setError(null);
    setPhase("running");
    setSteps(PRE_STEPS);
    setShown(0);
    const started = Date.now();
    const tick = window.setInterval(() => setShown((s) => Math.min(s + 1, PRE_STEPS.length)), 350);
    try {
      const d = await api<Draft>(`/hospital/encounters/${encounterId}/ai-draft`, { body: {} });
      window.setTimeout(() => {
        window.clearInterval(tick);
        setSteps([...PRE_STEPS, ...d.output.analysis_trace]);
        setShown(PRE_STEPS.length);
        setPending(d);
        setPhase("revealing");
      }, Math.max(0, 1100 - (Date.now() - started)));
    } catch (e) {
      window.clearInterval(tick);
      setError((e as Error).message);
      setPhase("idle");
    }
  };

  // Reveal the real analysis trace one step at a time.
  useEffect(() => {
    if (phase !== "revealing") return;
    if (shown >= steps.length) {
      const id = window.setTimeout(() => {
        if (pending) qc.setQueryData(key, pending);
        setPhase("idle");
      }, 300);
      return () => window.clearTimeout(id);
    }
    const id = window.setTimeout(() => setShown((s) => s + 1), 220);
    return () => window.clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, shown, steps.length, pending]);

  const decide = useMutation({
    mutationFn: (v: { action: "accepted" | "rejected"; rationale?: string }) =>
      api<Draft>(`/hospital/ai-drafts/${latest?.id}`, { method: "PATCH", body: v }),
    onSuccess: (d) => {
      qc.setQueryData(key, d);
      void qc.invalidateQueries({ queryKey: ["encounter", encounterId] });
    },
  });

  const order = async (test: string) => {
    const code = TEST_CODES.find(([re]) => re.test(test))?.[1];
    if (!code) return;
    await api(`/hospital/encounters/${encounterId}/orders`, { body: { items: [{ test_code: code }] } });
    onOrdered();
  };

  const d = phase === "idle" ? latest : null;
  return (
    <div ref={root} className="scroll-mt-24 overflow-hidden rounded-lg border border-border border-l-4 border-l-ai bg-card">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border px-5 py-4">
        <div className="flex items-start gap-3">
          <BrainCircuit className="mt-0.5 size-6 shrink-0 text-ai" />
          <div>
            <h3 className="text-lg font-semibold">VITALIS AI <span className="font-normal text-muted-foreground">· decision support</span></h3>
            <p className="text-sm text-muted-foreground">
              Reads today&apos;s visit with earlier visits, labs and the patient&apos;s record from other hospitals. Runs on VITALIS
              servers with risk models trained by our team.
            </p>
          </div>
        </div>
        {d && phase === "idle" ? <Button variant="outline" size="sm" onClick={run}>Run again</Button> : null}
      </div>

      {!d && phase === "idle" ? (
        <div className="flex flex-col items-start gap-4 px-5 py-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-xl text-muted-foreground">
            Suggests possible conditions with the evidence for each, and checks common treatments against this patient&apos;s
            allergies and medicines from every hospital. It never prescribes.
          </p>
          <Button size="lg" className="bg-ai text-white hover:opacity-90" onClick={run}><Sparkles className="size-5" /> Run VITALIS AI</Button>
        </div>
      ) : null}
      {error ? <div className="px-5 pb-4 text-sm text-emergency">{error}</div> : null}

      {phase !== "idle" ? (
        <ol className="space-y-2 px-5 py-5" aria-live="polite">
          {steps.slice(0, Math.max(1, shown + (phase === "running" ? 1 : 0))).map((s, i) => {
            const done = i < shown;
            const key = /trend|model|avoid|Red-flag/i.test(s);
            return (
              <li key={i} className="flex items-start gap-3">
                <span className={cn("mt-0.5 grid size-5 shrink-0 place-items-center rounded-full", done ? "bg-ai text-white" : "border-2 border-ai/40")}>
                  {done ? <Check className="size-3" strokeWidth={3} /> : null}
                </span>
                <span className={cn(done ? "" : "text-muted-foreground", key && done && "font-semibold")}>{s}</span>
              </li>
            );
          })}
        </ol>
      ) : null}

      {d ? <Body d={d} canOrder={canOrder} onOrder={order} onDecide={(a, r) => decide.mutate({ action: a, rationale: r })}
        busy={decide.isPending} error={decide.error ? (decide.error as Error).message : null} /> : null}
    </div>
  );
}

function Section({ title, subtitle, icon, children, className }: { title: string; subtitle?: string; icon?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={cn("px-5 py-4", className)}>
      <h4 className="flex items-center gap-1.5 font-semibold">{icon ? <span className="text-muted-foreground">{icon}</span> : null}{title}</h4>
      {subtitle ? <p className="mt-0.5 text-sm text-muted-foreground">{subtitle}</p> : null}
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Body({ d, canOrder, onOrder, onDecide, busy, error }: {
  d: Draft; canOrder: boolean; onOrder: (t: string) => Promise<void>; onDecide: (a: "accepted" | "rejected", r?: string) => void;
  busy: boolean; error: string | null;
}) {
  const a = d.output;
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const avoid = a.medication_options.filter((m) => m.safety === "avoid");
  return (
    <div className="divide-y divide-border">
      <Section title="Summary">
        <p className="leading-relaxed">{a.narrative?.summary ?? a.summary}</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Based on {a.data_coverage.prior_visits} earlier visit(s), {a.data_coverage.vital_readings} vital-sign readings and{" "}
          {a.data_coverage.lab_values} lab values.
        </p>
      </Section>

      {a.red_flags.length || avoid.length ? (
        <section className="space-y-3 px-5 py-4">
          {a.red_flags.map((f, i) => (
            <div key={i} className="flex gap-3 rounded-md border border-emergency/20 border-l-4 border-l-emergency bg-emergency-soft p-4">
              <AlertOctagon className="mt-0.5 size-5 shrink-0 text-emergency" />
              <div>
                <div className="font-semibold text-emergency">{f.title}</div>
                <div className="text-sm text-emergency">{f.detail}</div>
                <div className="mt-1 text-sm"><b>Do now:</b> {f.action}</div>
              </div>
            </div>
          ))}
          {avoid.map((m) => (
            <div key={m.drug} className="flex gap-3 rounded-md border border-emergency/20 border-l-4 border-l-emergency bg-card p-4">
              <ShieldAlert className="mt-0.5 size-5 shrink-0 text-emergency" />
              <div>
                <div className="text-sm font-semibold text-emergency">Safety alert from the patient&apos;s record</div>
                <div className="mt-0.5 font-semibold">Do not give {m.drug.split(" ")[0]}. It is a usual {m.for_condition} medicine, but it conflicts with this patient&apos;s history.</div>
                {m.alerts.map((al, i) => <div key={i} className="mt-1 text-sm text-muted-foreground">{al}</div>)}
              </div>
            </div>
          ))}
        </section>
      ) : null}

      <Section title="Possible conditions to consider" subtitle="Ranked by the evidence in the record. Estimates, not diagnoses.">
        <div className="space-y-2">
          {a.conditions.map((c, i) => <ConditionCard key={c.condition} c={c} open={i === 0} canOrder={canOrder} onOrder={onOrder} />)}
        </div>
      </Section>

      {a.medication_options.length ? (
        <Section title="Treatment options, checked against the record" subtitle="Drug names only. The doctor decides and writes any prescription and dose.">
          <div className="divide-y divide-border rounded-md border border-border">
            {a.medication_options.map((m, i) => (
              <div key={i} className={cn("grid gap-x-4 gap-y-1 px-4 py-3 sm:grid-cols-[110px_1fr]", m.safety === "avoid" && "bg-emergency-soft")}>
                <div>
                  {m.safety === "ok" ? <Badge tone="ok"><CheckCircle2 className="size-3.5" />No conflict</Badge> : null}
                  {m.safety === "caution" ? <Badge tone="warn"><TriangleAlert className="size-3.5" />Caution</Badge> : null}
                  {m.safety === "avoid" ? <Badge tone="danger"><CircleSlash className="size-3.5" />Avoid</Badge> : null}
                </div>
                <div className="min-w-0">
                  <div className={cn("font-semibold", m.safety === "avoid" && "text-emergency line-through")}>{m.drug}</div>
                  <div className="text-sm text-muted-foreground">{m.rationale}</div>
                  {m.alerts.map((al, k) => <div key={k} className={cn("mt-1 text-sm", m.safety === "avoid" ? "font-medium text-emergency" : "text-warning")}>{al}</div>)}
                </div>
              </div>
            ))}
          </div>
        </Section>
      ) : null}

      {a.ml_models.length ? (
        <Section title="Risk models trained by the VITALIS team" subtitle="We show exactly which inputs were measured and which were assumed.">
          <div className="grid gap-3 xl:grid-cols-2">{a.ml_models.map((m) => <ModelCard key={m.key} m={m} />)}</div>
        </Section>
      ) : null}

      <section className="grid gap-6 px-5 py-4 md:grid-cols-2">
        <div>
          <h4 className="flex items-center gap-1.5 font-semibold"><TrendingUp className="size-4 text-muted-foreground" />Changes over time</h4>
          <ul className="mt-2 space-y-1.5">
            {a.trends.map((t) => (
              <li key={t.metric} className="flex gap-2 text-sm">
                <span className={cn("mt-1.5 size-1.5 shrink-0 rounded-full", t.direction === "rising" ? "bg-emergency" : t.direction === "falling" ? "bg-info" : "bg-border")} />
                {t.text}
              </li>
            ))}
            {!a.trends.length ? <li className="text-sm text-muted-foreground">Not enough earlier readings for a trend.</li> : null}
          </ul>
        </div>
        <div>
          <h4 className="flex items-center gap-1.5 font-semibold"><Info className="size-4 text-muted-foreground" />What would make this more certain</h4>
          <ul className="mt-2 space-y-1.5">
            {a.missing_data.map((m, i) => <li key={i} className="flex gap-2 text-sm"><span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-warning" />{m}</li>)}
            {!a.missing_data.length ? <li className="text-sm text-muted-foreground">Key information is complete.</li> : null}
          </ul>
        </div>
      </section>

      <section className="bg-muted px-5 py-4">
        <div className="text-sm text-muted-foreground"><b className="text-foreground">You decide.</b> {a.safety_disclaimer}</div>
        {d.action === "pending" && !rejecting ? (
          <div className="mt-3 flex flex-wrap justify-end gap-2">
            <Button variant="outline" onClick={() => setRejecting(true)}><X className="size-4" />Reject</Button>
            <Button disabled={busy} onClick={() => onDecide("accepted")}><Check className="size-4" />Accept and draft note</Button>
          </div>
        ) : null}
        {d.action === "accepted" ? <Badge tone="ok" className="mt-3"><Check className="size-3.5" />Accepted. Draft added to your note</Badge> : null}
        {d.action === "rejected" ? <Badge className="mt-3">Rejected: {d.rationale}</Badge> : null}
        {rejecting && d.action === "pending" ? (
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <input className={cn(inputCls, "flex-1")} placeholder="Why? (kept in the audit log)" value={reason} onChange={(e) => setReason(e.target.value)} />
            <Button variant="ghost" onClick={() => setRejecting(false)}>Cancel</Button>
            <Button variant="emergency" disabled={!reason.trim() || busy} onClick={() => onDecide("rejected", reason)}>Reject</Button>
          </div>
        ) : null}
        {error ? <p className="mt-2 text-sm text-emergency">{error}</p> : null}
        <div className="mt-2 font-mono text-xs text-muted-foreground">{a.engine_version} · narrative: {d.narrative_provider}</div>
      </section>
    </div>
  );
}

const KIND: Record<Evidence["kind"], { icon: React.ReactNode; label: string }> = {
  current: { icon: <Sparkles />, label: "Today" },
  history: { icon: <History />, label: "History" },
  lab: { icon: <FlaskConical />, label: "Lab" },
  family: { icon: <Users />, label: "Family" },
  ml: { icon: <Cpu />, label: "Model" },
  rule: { icon: <BookOpen />, label: "Guideline" },
};

function ConditionCard({ c, open: initial, canOrder, onOrder }: { c: Condition; open?: boolean; canOrder: boolean; onOrder: (t: string) => Promise<void> }) {
  const [open, setOpen] = useState(!!initial);
  const [ordered, setOrdered] = useState<string[]>([]);
  const pct = Math.round(c.likelihood * 100);
  return (
    <Card className={cn("p-0", open && "border-ai/30")}>
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="flex w-full items-center gap-4 px-4 py-3 text-left">
        <span className="grid size-8 shrink-0 place-items-center rounded-full bg-foreground text-sm font-semibold text-background">{c.rank}</span>
        <div className="min-w-0 flex-1">
          <div className="font-semibold">{c.condition}</div>
          <div className="mt-1.5 flex items-center gap-3">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted" role="meter" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Likelihood">
              <div className="h-full rounded-full bg-ai transition-[width] duration-500" style={{ width: `${pct}%` }} />
            </div>
            <span className="w-36 shrink-0 text-right text-sm font-semibold">{c.likelihood_label} likelihood</span>
          </div>
        </div>
        <ChevronDown className={cn("size-5 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} />
      </button>
      {open ? (
        <div className="space-y-5 border-t border-border px-4 py-4">
          <div>
            <div className="mb-2 text-sm font-semibold">Why this is suggested</div>
            <ul className="space-y-2.5">
              {c.evidence.map((e, i) => (
                <li key={i} className="flex gap-3">
                  <span className="mt-0.5 inline-flex h-6 w-24 shrink-0 items-center gap-1 rounded-md bg-muted px-2 text-xs font-medium [&>svg]:size-3.5">{KIND[e.kind]?.icon}{KIND[e.kind]?.label}</span>
                  <div className="min-w-0"><div className="text-sm">{e.text}</div><div className="text-xs text-muted-foreground">{e.source}</div></div>
                </li>
              ))}
            </ul>
            {c.against.length ? (
              <>
                <div className="mb-1.5 mt-4 text-sm font-semibold">Against</div>
                <ul className="space-y-1">{c.against.map((e, i) => <li key={i} className="text-sm text-muted-foreground">{e.text}</li>)}</ul>
              </>
            ) : null}
            <div className="mt-4 flex items-center gap-1.5 text-xs text-muted-foreground"><BookOpen className="size-3.5" />{c.guideline}</div>
          </div>
          <div className="grid gap-5 sm:grid-cols-2">
            <div>
              <div className="mb-2 text-sm font-semibold">Suggested tests</div>
              <div className="divide-y divide-border rounded-md border border-border">
                {c.recommended_investigations.map((t) => {
                  const orderable = canOrder && TEST_CODES.some(([re]) => re.test(t));
                  return (
                    <div key={t} className="flex items-center justify-between gap-2 px-3 py-2 text-sm">
                      <span>{t}</span>
                      {ordered.includes(t) ? <span className="inline-flex items-center gap-1 text-xs font-semibold text-primary"><Check className="size-3.5" />Ordered</span>
                        : orderable ? (
                          <button type="button" onClick={async () => { await onOrder(t); setOrdered([...ordered, t]); }}
                            className="inline-flex h-8 shrink-0 items-center gap-1 rounded-md px-2 text-sm font-semibold text-primary hover:bg-mint">
                            <Plus className="size-4" />Order
                          </button>
                        ) : null}
                    </div>
                  );
                })}
              </div>
            </div>
            <div>
              <div className="mb-2 text-sm font-semibold">Things to consider</div>
              <ul className="space-y-1">{c.management_considerations.map((m) => <li key={m} className="flex gap-2 text-sm"><span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-muted-foreground" />{m}</li>)}</ul>
            </div>
          </div>
        </div>
      ) : null}
    </Card>
  );
}

const SRC: Record<string, string> = { measured: "text-primary", derived: "text-info", record: "text-foreground", assumed: "text-warning", imputed: "text-warning" };

function ModelCard({ m }: { m: ModelRun }) {
  const [open, setOpen] = useState(false);
  const BANDS = ["Low", "Moderate", "High"];
  const idx = BANDS.indexOf(m.band);
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0"><div className="font-semibold">{m.name}</div><div className="text-sm text-muted-foreground">{m.algorithm}</div></div>
        <div className="text-right" title="Model score, not a validated clinical probability">
          <div className="text-2xl font-semibold text-ai">{m.band}</div>
          <div className="whitespace-nowrap text-xs text-muted-foreground">screening band</div>
          <div className="whitespace-nowrap font-mono text-[11px] text-muted-foreground">model score {m.probability.toFixed(2)}</div>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-1" aria-hidden>{BANDS.map((b, i) => <div key={b} className={cn("h-1.5 rounded-full", i <= idx ? "bg-ai" : "bg-muted")} />)}</div>
      <p className="mt-2 text-xs text-muted-foreground">{m.note}</p>
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open}
        className="mt-3 flex w-full items-center justify-between rounded-md border border-border px-3 py-2 text-sm hover:bg-muted">
        <span>{m.measured_inputs} of {m.total_inputs} inputs came from the patient&apos;s record</span>
        <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} />
      </button>
      {open ? (
        <div className="mt-2 divide-y divide-border">
          {m.inputs.map((i) => (
            <div key={i.feature} className="flex items-center justify-between gap-2 py-1.5 text-sm" title={i.detail}>
              <span className="text-muted-foreground">{i.label}</span>
              <span className="flex items-center gap-2"><b className="tabular-nums">{i.value}</b><span className={cn("w-16 text-right text-xs font-semibold capitalize", SRC[i.source])}>{i.source}</span></span>
            </div>
          ))}
        </div>
      ) : null}
      <div className="mt-2 font-mono text-[11px] text-muted-foreground">{m.model_version}</div>
    </Card>
  );
}
