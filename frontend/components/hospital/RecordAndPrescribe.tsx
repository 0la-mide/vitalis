"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, CircleSlash, Pill, Plus, ShieldCheck, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/card";
import { inputCls } from "@/components/ui/field";
import { api, ApiError, type Schemas } from "@/lib/api";
import { cn } from "@/lib/utils";

type Rec = Schemas["RecordOut"];
type Safety = { verdict: "ok" | "caution" | "avoid"; alerts: { kind: string; severity: string; text: string; source: string | null }[] };

const KINDS = [
  { kind: "allergy", title: "Allergies", tone: "danger" as const },
  { kind: "condition", title: "Conditions", tone: "neutral" as const },
  { kind: "medication", title: "Current medicines", tone: "neutral" as const },
  { kind: "family", title: "Family history", tone: "neutral" as const },
];

export function useRecord(encounterId: string) {
  return useQuery({ queryKey: ["record", encounterId], queryFn: () => api<Rec>(`/hospital/encounters/${encounterId}/record`) });
}

/** The patient's record across hospitals: every entry says where and when it was recorded. */
export function RecordCard({ encounterId, canAdd }: { encounterId: string; canAdd: boolean }) {
  const qc = useQueryClient();
  const { data } = useRecord(encounterId);
  const [adding, setAdding] = useState(false);
  const add = useMutation({
    mutationFn: (body: object) => api<Rec>(`/hospital/encounters/${encounterId}/history`, { body }),
    onSuccess: (r) => {
      qc.setQueryData(["record", encounterId], r);
      setAdding(false);
    },
  });
  const rows = data?.history ?? [];
  const allergies = rows.filter((h) => h.kind === "allergy");
  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-bold">Patient record</h2>
        {canAdd ? <Button size="sm" variant="outline" onClick={() => setAdding(!adding)}><Plus className="size-4" />Add</Button> : null}
      </div>
      {allergies.length ? (
        <div className="rounded-md border border-emergency/20 border-l-4 border-l-emergency bg-emergency-soft px-3 py-2 text-sm">
          <b className="text-emergency">Allergies:</b>{" "}
          {allergies.map((a) => `${a.text}${a.detail ? ` (${a.detail})` : ""}`).join("; ")}
        </div>
      ) : <div className="text-sm text-muted-foreground">No known allergies recorded.</div>}
      {data?.hidden_from_other_hospitals ? (
        <p className="text-xs text-muted-foreground">
          {data.hidden_from_other_hospitals} more entr{data.hidden_from_other_hospitals === 1 ? "y" : "ies"} from other hospitals: visible once the patient shares their record.
        </p>
      ) : null}
      <div className="grid gap-3 sm:grid-cols-2">
        {KINDS.filter((k) => k.kind !== "allergy").map((k) => {
          const items = rows.filter((h) => h.kind === k.kind);
          return (
            <div key={k.kind}>
              <div className="text-xs font-semibold uppercase text-muted-foreground">{k.title}</div>
              <ul className="mt-1 space-y-1">
                {items.map((h) => (
                  <li key={h.id} className="text-sm">
                    {k.kind === "family" ? `${h.detail ?? "Relative"}: ${h.text}${h.onset_age ? ` (onset ${h.onset_age})` : ""}` : h.text}
                    {k.kind === "medication" && h.detail ? <span className="text-muted-foreground"> · {h.detail}</span> : null}
                    <span className="block text-xs text-muted-foreground">
                      {h.here ? "Recorded here" : h.source} · {new Date(h.recorded_at).toLocaleDateString()}
                    </span>
                  </li>
                ))}
                {!items.length ? <li className="text-sm text-muted-foreground">—</li> : null}
              </ul>
            </div>
          );
        })}
      </div>
      {adding ? (
        <form className="grid gap-2 rounded-md bg-muted p-3 sm:grid-cols-[140px_1fr_1fr_auto]" onSubmit={(e) => {
          e.preventDefault();
          const fd = new FormData(e.currentTarget);
          add.mutate({ kind: fd.get("kind"), text: fd.get("text"), detail: fd.get("detail") || null });
        }}>
          <select name="kind" className={inputCls}>
            <option value="allergy">Allergy</option><option value="condition">Condition</option>
            <option value="medication">Medicine</option><option value="family">Family history</option>
          </select>
          <input name="text" required minLength={2} placeholder="e.g. Penicillin / Asthma / Metformin" className={inputCls} />
          <input name="detail" placeholder="Reaction / dose / relative" className={inputCls} />
          <Button type="submit" disabled={add.isPending}>Save</Button>
          {add.error ? <p className="text-sm text-emergency sm:col-span-4">{(add.error as Error).message}</p> : null}
        </form>
      ) : null}
    </Card>
  );
}

/** Prescribe with a safety check against allergies, medicines and conditions recorded at every hospital. */
export function PrescribeCard({ encounterId }: { encounterId: string }) {
  const qc = useQueryClient();
  const { data } = useRecord(encounterId);
  const [drug, setDrug] = useState("");
  const [dose, setDose] = useState("");
  const [override, setOverride] = useState("");
  const [safety, setSafety] = useState<Safety | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const check = async () => {
    setBusy(true);
    setError(null);
    try {
      setSafety(await api<Safety>(`/hospital/encounters/${encounterId}/prescriptions/check`, { body: { drug } }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await api<Rec>(`/hospital/encounters/${encounterId}/prescriptions`, {
        body: { drug, dose, ...(override.trim() ? { override_reason: override } : {}) },
      });
      qc.setQueryData(["record", encounterId], r);
      void qc.invalidateQueries({ queryKey: ["encounter", encounterId] });
      setDrug(""); setDose(""); setOverride(""); setSafety(null);
    } catch (e) {
      if (e instanceof ApiError && e.code === "safety_conflict") setSafety(e.details as Safety);
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="space-y-3">
      <h2 className="flex items-center gap-2 font-bold"><Pill className="size-5 text-muted-foreground" />Prescribe</h2>
      <div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
        <input value={drug} onChange={(e) => { setDrug(e.target.value); setSafety(null); }} placeholder="Medicine, e.g. Lisinopril" className={inputCls} />
        <input value={dose} onChange={(e) => setDose(e.target.value)} placeholder="Dose and duration, e.g. 10 mg once daily" className={inputCls} />
        <Button variant="outline" disabled={drug.trim().length < 2 || busy} onClick={check}><ShieldCheck className="size-4" />Check safety</Button>
      </div>
      {safety ? (
        <div className={cn("rounded-md border p-3 text-sm",
          safety.verdict === "avoid" ? "border-emergency/30 bg-emergency-soft" : safety.verdict === "caution" ? "border-warning/30 bg-warning-soft" : "border-mint-strong bg-mint")}>
          <div className="flex items-center gap-2 font-semibold">
            {safety.verdict === "ok" ? <><CheckCircle2 className="size-4 text-primary" />No conflict with this patient&apos;s record</> : null}
            {safety.verdict === "caution" ? <><TriangleAlert className="size-4 text-warning" />Caution</> : null}
            {safety.verdict === "avoid" ? <><CircleSlash className="size-4 text-emergency" /><span className="text-emergency">Blocked: conflicts with the record</span></> : null}
          </div>
          {safety.alerts.map((a, i) => (
            <div key={i} className="mt-1">{a.text}{a.source ? <span className="text-muted-foreground"> Recorded at {a.source}.</span> : null}</div>
          ))}
          {safety.verdict === "avoid" ? (
            <input value={override} onChange={(e) => setOverride(e.target.value)} className={cn(inputCls, "mt-2")}
              placeholder="To prescribe anyway, give a clinical reason (audited)" />
          ) : null}
        </div>
      ) : null}
      <div className="flex justify-end">
        <Button disabled={!safety || !dose.trim() || busy || (safety.verdict === "avoid" && !override.trim())} onClick={submit}>
          {safety?.verdict === "avoid" ? "Override and prescribe" : "Prescribe"}
        </Button>
      </div>
      {error && !(safety && safety.verdict === "avoid") ? <p className="text-sm text-emergency">{error}</p> : null}
      {data?.prescriptions.length ? (
        <ul className="divide-y divide-border rounded-md border border-border">
          {data.prescriptions.map((p) => (
            <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm">
              <span><b>{p.drug}</b> · {p.dose}</span>
              <span className="flex items-center gap-2 text-xs text-muted-foreground">
                {p.override_reason ? <Badge tone="warn">override: {p.override_reason}</Badge> : null}
                {p.prescribed_by} · {new Date(p.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </Card>
  );
}
