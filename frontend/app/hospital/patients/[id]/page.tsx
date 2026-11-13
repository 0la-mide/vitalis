"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowRight, ArrowUp, CircleAlert, FileSignature, FlaskConical, Siren } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { AIPanel } from "@/components/hospital/AIPanel";
import { NetworkRecordCard } from "@/components/hospital/NetworkRecord";
import { PrescribeCard, RecordCard } from "@/components/hospital/RecordAndPrescribe";
import { useFacilityStream } from "@/components/hospital/useFacilityStream";
import { useMe } from "@/lib/staff";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/card";
import { inputCls } from "@/components/ui/field";
import { api, type Schemas } from "@/lib/api";
import { ROLE_LABEL } from "@/lib/staff";
import { clockTime, cn, timeAgo } from "@/lib/utils";
import { VITAL_FIELDS, vitalLabel } from "@/lib/vitals";

type Enc = Schemas["EncounterOut"];
type Vital = Schemas["VitalRow"];
type Mutate = (path: string, body?: unknown) => Promise<void>;

const AGE: Record<string, string> = { under5: "Under 5", child: "Child 5–12", teen: "Teen", adult: "Adult", elderly: "Elderly" };
const NEXT_LABEL: Record<string, string> = {
  awaiting_nursing: "Send to nursing",
  awaiting_doctor: "Send to doctor",
  awaiting_disposition: "Decide disposition",
  completed: "Complete encounter",
};

export default function EncounterPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const key = ["encounter", id];
  const { data: e, error } = useQuery({ queryKey: key, queryFn: () => api<Enc>(`/hospital/encounters/${id}`) });
  const { data: me } = useMe();
  const isDoctor = me?.role === "doctor";
  useFacilityStream([key, ["encounters"]]);
  const [err, setErr] = useState<string | null>(null);

  const m = useMutation({
    mutationFn: ({ path, body }: { path: string; body?: unknown }) =>
      api<Enc>(`/hospital/encounters/${id}${path}`, { body: body ?? {} }),
    onSuccess: (data) => {
      setErr(null);
      qc.setQueryData(key, data);
      void qc.invalidateQueries({ queryKey: ["encounters"] });
    },
    onError: (x) => setErr((x as Error).message),
  });
  const mutate: Mutate = async (path, body) => {
    await m.mutateAsync({ path, body }).catch(() => {});
  };

  if (error) return <Card>{(error as Error).message}</Card>;
  if (!e) return <p className="text-muted-foreground">Loading…</p>;
  const closed = e.state === "completed" || e.state === "cancelled";

  return (
    <div className="space-y-4">
      <Link href="/hospital/patients" className="text-sm text-muted-foreground hover:underline">← All patients</Link>
      <Card className={cn("flex flex-wrap items-start justify-between gap-3", e.emergency && "border-l-4 border-l-emergency")}>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-mono text-2xl font-bold">{e.patient.vitalis_id}</h1>
            {e.emergency ? <Badge tone="danger"><Siren className="h-3.5 w-3.5" /> Emergency</Badge> : null}
          </div>
          <p className="text-sm text-muted-foreground">
            {AGE[e.patient.age_group ?? ""] ?? "Age ?"} · {e.patient.sex ?? "sex ?"}
            {e.patient.pregnant ? " · pregnant" : ""} · in since {clockTime(e.created_at)}
          </p>
          {e.chief_complaint ? <p className="mt-1">Complaint: {e.chief_complaint}</p> : null}
        </div>
        <div className="text-right">
          <Badge tone={closed ? "neutral" : e.state === "results_ready" ? "ok" : "warn"} className="text-sm">{e.state_label}</Badge>
          {e.disposition ? <p className="mt-1 text-sm">Disposition: <b>{e.disposition}</b>{e.disposition_note ? ` — ${e.disposition_note}` : ""}</p> : null}
          {e.cancel_reason ? <p className="mt-1 text-sm">Cancelled: {e.cancel_reason}</p> : null}
        </div>
      </Card>

      {err ? <p className="rounded-lg bg-emergency-soft p-2 text-sm text-emergency">{err}</p> : null}
      <Actions e={e} mutate={mutate} busy={m.isPending} />

      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          {e.referral ? <ReferralCard r={e.referral} /> : null}
          <RecordCard encounterId={e.id} canAdd={!closed && (me?.role === "nurse" || isDoctor)} />
          <NetworkRecordCard patientId={e.patient_id} encounterId={e.id} />
          <VitalsCard e={e} mutate={mutate} busy={m.isPending} />
          {isDoctor && !closed ? (
            <AIPanel encounterId={e.id} canOrder={e.allowed.order_tests}
              onOrdered={() => void qc.invalidateQueries({ queryKey: key })} />
          ) : null}
          <NotesCard e={e} mutate={mutate} busy={m.isPending} />
          <OrdersCard e={e} mutate={mutate} busy={m.isPending} />
          {isDoctor && !closed ? <PrescribeCard encounterId={e.id} /> : null}
        </div>
        <Timeline e={e} />
      </div>
    </div>
  );
}

function Actions({ e, mutate, busy }: { e: Enc; mutate: Mutate; busy: boolean }) {
  const [dispo, setDispo] = useState(false);
  const [cancel, setCancel] = useState(false);
  const [disposition, setDisposition] = useState("discharged");
  const [text, setText] = useState("");
  const moves = e.allowed.transitions;
  if (!moves.length && !e.allowed.cancel) return null;
  return (
    <Card className="flex flex-wrap items-center gap-2">
      <span className="mr-2 text-sm font-semibold text-muted-foreground">Next step</span>
      {moves.filter((t) => t !== "awaiting_disposition").map((t) => (
        <Button key={t} disabled={busy} onClick={() => mutate("/transition", { to: t })}>
          {NEXT_LABEL[t] ?? t.replace(/_/g, " ")}
        </Button>
      ))}
      {moves.includes("awaiting_disposition") ? (
        <Button variant={dispo ? "mint" : "primary"} onClick={() => { setDispo(!dispo); setCancel(false); }}>
          Decide disposition
        </Button>
      ) : null}
      {e.allowed.cancel ? (
        <Button variant="ghost" onClick={() => { setCancel(!cancel); setDispo(false); }}>Cancel encounter</Button>
      ) : null}
      {dispo ? (
        <div className="flex w-full flex-wrap gap-2 rounded-lg bg-muted p-2">
          <select value={disposition} onChange={(x) => setDisposition(x.target.value)} className={cn(inputCls, "w-44")}>
            <option value="discharged">Discharged home</option>
            <option value="admitted">Admitted</option>
            <option value="transferred">Transferred</option>
            <option value="left">Left against advice</option>
          </select>
          <input value={text} onChange={(x) => setText(x.target.value)} placeholder="Instructions / ward / destination"
            className={cn(inputCls, "min-w-48 flex-1")} />
          <Button disabled={busy} onClick={() => mutate("/transition", { to: "awaiting_disposition", disposition, note: text })}>
            Confirm
          </Button>
        </div>
      ) : null}
      {cancel ? (
        <div className="flex w-full gap-2 rounded-lg bg-muted p-2">
          <input value={text} onChange={(x) => setText(x.target.value)} placeholder="Reason" className={cn(inputCls, "flex-1")} />
          <Button variant="outline" disabled={!text.trim() || busy}
            onClick={() => mutate("/transition", { to: "cancelled", reason: text })}>Confirm cancel</Button>
        </div>
      ) : null}
    </Card>
  );
}

function ReferralCard({ r }: { r: NonNullable<Enc["referral"]> }) {
  return (
    <Card className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-bold">Referral</h2>
        <span className="text-sm text-muted-foreground">
          {r.referred_by ? `via ${r.referred_by} · ` : "family app · "}sent {clockTime(r.sent_at)}
          {r.arrived_at ? ` · arrived ${clockTime(r.arrived_at)}` : ""}
        </span>
      </div>
      {r.red_flag_message ? (
        <p className="flex items-start gap-2 rounded-lg bg-emergency-soft p-2 text-sm font-semibold text-emergency">
          <Siren className="mt-0.5 h-4 w-4 shrink-0" /> {r.red_flag_message}
        </p>
      ) : null}
      <div className="flex flex-wrap gap-1.5">
        {r.care_label ? <Badge tone="info">{r.care_label}</Badge> : null}
        {r.symptoms.map((s) => (
          <span key={s.code} className="rounded-md bg-muted px-2 py-1 text-sm">
            {s.label}{s.severity ? ` · ${s.severity}/5` : ""}{s.onset ? ` · ${s.onset}` : ""}
          </span>
        ))}
      </div>
    </Card>
  );
}

function Trend({ before, now }: { before?: Vital; now?: Vital }) {
  if (!before || !now) return null;
  const d = now.value - before.value;
  const Icon = Math.abs(d) < 0.05 ? ArrowRight : d > 0 ? ArrowUp : ArrowDown;
  return <Icon className="h-4 w-4 text-muted-foreground" aria-label={d > 0 ? "up" : d < 0 ? "down" : "same"} />;
}

function VitalsCard({ e, mutate, busy }: { e: Enc; mutate: Mutate; busy: boolean }) {
  const [correcting, setCorrecting] = useState<Vital | null>(null);
  const current = e.vitals.filter((v) => !v.superseded);
  const last = (src: string, kind: string) => [...current].reverse().find((v) => v.kind === kind && v.source === src);
  const kinds = VITAL_FIELDS.map((f) => f.kind).filter((k) => current.some((v) => v.kind === k));
  const hasWorker = current.some((v) => v.source === "worker");

  return (
    <Card className="space-y-3">
      <h2 className="font-bold">Vitals</h2>
      {kinds.length ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase text-muted-foreground">
              <tr>
                <th className="py-1 pr-3">Vital</th>
                {hasWorker ? <th className="py-1 pr-3">Before arrival (chemist)</th> : null}
                <th className="py-1 pr-3">Hospital (latest)</th>
                <th className="py-1" />
              </tr>
            </thead>
            <tbody>
              {kinds.map((k) => {
                const w = last("worker", k);
                const n = last("nurse", k);
                return (
                  <tr key={k} className="border-t border-border">
                    <td className="py-1.5 pr-3 font-medium">{vitalLabel(k)}</td>
                    {hasWorker ? (
                      <td className="py-1.5 pr-3">{w ? <>{w.value} {w.unit} <span className="text-xs text-muted-foreground">{clockTime(w.measured_at)}</span></> : "—"}</td>
                    ) : null}
                    <td className="py-1.5 pr-3">
                      {n ? (
                        <span className="inline-flex items-center gap-1.5">
                          <Trend before={w} now={n} />
                          <b>{n.value}</b> {n.unit}
                          <span className="text-xs text-muted-foreground">{clockTime(n.measured_at)}</span>
                          {n.urgent ? <Badge tone="danger"><CircleAlert className="h-3 w-3" /> urgent</Badge> : null}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="py-1.5 text-right">
                      {n && e.allowed.record_vitals ? (
                        <button type="button" className="text-xs text-muted-foreground underline" onClick={() => setCorrecting(n)}>
                          correct
                        </button>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : <p className="text-sm text-muted-foreground">No vitals yet.</p>}

      {e.vitals.some((v) => v.superseded) ? (
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer">Corrected readings (originals kept)</summary>
          <ul className="mt-1 space-y-0.5">
            {e.vitals.filter((v) => v.superseded).map((v) => (
              <li key={v.id} className="line-through">{vitalLabel(v.kind)} {v.value} {v.unit} · {v.entered_by} · {clockTime(v.measured_at)}</li>
            ))}
          </ul>
        </details>
      ) : null}

      {correcting ? (
        <form className="flex flex-wrap items-end gap-2 rounded-lg bg-muted p-2" onSubmit={async (x) => {
          x.preventDefault();
          const fd = new FormData(x.currentTarget);
          await mutate("/vitals", { readings: [{ kind: correcting.kind, value: Number(fd.get("value")) }],
            corrected_from: correcting.id, correction_reason: fd.get("reason") });
          setCorrecting(null);
        }}>
          <span className="text-sm">Correct {vitalLabel(correcting.kind)} ({correcting.value})</span>
          <input name="value" type="number" step="0.1" required className={cn(inputCls, "w-28")} />
          <input name="reason" required placeholder="Reason" className={cn(inputCls, "min-w-40 flex-1")} />
          <Button type="submit" size="sm" disabled={busy}>Save correction</Button>
          <Button type="button" size="sm" variant="ghost" onClick={() => setCorrecting(null)}>Cancel</Button>
        </form>
      ) : null}

      {e.allowed.record_vitals ? (
        <form className="grid grid-cols-2 gap-2 sm:grid-cols-4" onSubmit={async (x) => {
          x.preventDefault();
          const form = x.currentTarget;
          const fd = new FormData(form);
          const readings = VITAL_FIELDS.flatMap((f) => {
            const raw = String(fd.get(f.kind) ?? "").trim();
            return raw ? [{ kind: f.kind, value: Number(raw) }] : [];
          });
          if (!readings.length) return;
          await mutate("/vitals", { readings });
          form.reset();
        }}>
          {VITAL_FIELDS.map((f) => (
            <label key={f.kind} className="grid min-w-0 gap-0.5 text-xs font-medium">
              <span>{f.label} <span className="font-normal text-muted-foreground">({f.unit})</span></span>
              <input name={f.kind} type="number" inputMode="decimal" step={f.step} className={cn(inputCls, "h-10 min-w-0")} />
            </label>
          ))}
          <div className="flex items-end"><Button type="submit" className="w-full" disabled={busy}>Record vitals</Button></div>
        </form>
      ) : null}
    </Card>
  );
}

function NotesCard({ e, mutate, busy }: { e: Enc; mutate: Mutate; busy: boolean }) {
  const myDraft = e.notes.find((n) => n.status === "draft");
  const [text, setText] = useState<string | null>(null);
  const [amending, setAmending] = useState<string | null>(null);
  const value = text ?? myDraft?.body ?? "";
  const signed = e.notes.filter((n) => n.status === "signed");
  return (
    <Card className="space-y-3">
      <h2 className="font-bold">Clinical notes</h2>
      {signed.map((n) => (
        <div key={n.id} className="rounded-lg border border-border p-3">
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
            <span><FileSignature className="mr-1 inline h-3.5 w-3.5" />Signed by {n.author} · {clockTime(n.signed_at)} · v{n.version}</span>
            {e.allowed.write_notes ? (
              <button type="button" className="underline" onClick={() => { setAmending(n.id); setText(n.body); }}>amend</button>
            ) : null}
          </div>
          <p className="mt-1 whitespace-pre-wrap text-sm">{n.body}</p>
        </div>
      ))}
      {!signed.length && !e.allowed.write_notes ? <p className="text-sm text-muted-foreground">No signed notes yet.</p> : null}
      {e.allowed.write_notes ? (
        <div className="space-y-2">
          {amending ? <p className="text-xs text-muted-foreground">Amending: the signed note is kept; this becomes a new version.</p> : null}
          <textarea value={value} onChange={(x) => setText(x.target.value)} rows={5}
            placeholder="History, examination, assessment, plan…" className={cn(inputCls, "h-auto py-2")} />
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" disabled={busy || !value.trim()} onClick={async () => {
              await mutate("/notes", { body: value, note_id: amending ?? myDraft?.id });
              setAmending(null);
              setText(null);
            }}>
              Save draft
            </Button>
            {myDraft && !amending ? (
              <Button disabled={busy || text !== null} title={text !== null ? "Save the draft first" : undefined}
                onClick={() => mutate(`/notes/${myDraft.id}/sign`)}>
                <FileSignature className="h-4 w-4" /> Sign note
              </Button>
            ) : null}
            {myDraft ? <span className="self-center text-xs text-muted-foreground">Draft saved {timeAgo(myDraft.created_at)} — only you can see it</span> : null}
          </div>
        </div>
      ) : null}
    </Card>
  );
}

function OrdersCard({ e, mutate, busy }: { e: Enc; mutate: Mutate; busy: boolean }) {
  const { data: tests = [] } = useQuery({
    queryKey: ["tests"],
    queryFn: () => api<Schemas["TestOption"][]>("/hospital/tests"),
    staleTime: Infinity,
    enabled: e.allowed.order_tests,
  });
  const [picked, setPicked] = useState<Record<string, "routine" | "urgent">>({});
  const [open, setOpen] = useState(false);
  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-bold">Investigations</h2>
        {e.allowed.order_tests ? <Button size="sm" variant={open ? "mint" : "outline"} onClick={() => setOpen(!open)}>
          <FlaskConical className="h-4 w-4" /> Order tests</Button> : null}
      </div>
      {open ? (
        <div className="space-y-2 rounded-lg bg-muted p-2">
          {(["lab", "radiology"] as const).map((cat) => (
            <div key={cat}>
              <p className="text-xs font-semibold uppercase text-muted-foreground">{cat}</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {tests.filter((t) => t.category === cat).map((t) => {
                  const p = picked[t.code];
                  return (
                    <button key={t.code} type="button"
                      onClick={() => setPicked((s) => {
                        const n = { ...s };
                        if (!p) n[t.code] = "routine";
                        else if (p === "routine") n[t.code] = "urgent";
                        else delete n[t.code];
                        return n;
                      })}
                      className={cn("rounded-lg border px-2.5 py-1.5 text-sm",
                        p === "urgent" ? "border-emergency bg-emergency-soft text-emergency" : p ? "border-primary bg-mint" : "border-border bg-card")}>
                      {t.name}{p === "urgent" ? " · URGENT" : ""}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
          <p className="text-xs text-muted-foreground">Tap once to select, twice for urgent, three times to clear.</p>
          <Button disabled={busy || !Object.keys(picked).length} onClick={async () => {
            await mutate("/orders", { items: Object.entries(picked).map(([test_code, priority]) => ({ test_code, priority })) });
            setPicked({});
            setOpen(false);
          }}>Send {Object.keys(picked).length || ""} order(s) to lab</Button>
        </div>
      ) : null}
      {e.orders.length ? (
        <ul className="space-y-2">
          {e.orders.map((o) => (
            <li key={o.id} className="rounded-lg border border-border p-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium">{o.test_name} {o.priority === "urgent" ? <Badge tone="danger">urgent</Badge> : null}</span>
                <Badge tone={o.status === "verified" ? "ok" : o.status === "resulted" ? "warn" : "neutral"}>
                  {o.status === "resulted" ? "awaiting verification" : o.status === "collected" ? "sample collected" : o.status}
                </Badge>
              </div>
              {o.status === "verified" && o.result_text ? (
                <p className={cn("mt-1 whitespace-pre-wrap text-sm", o.abnormal && "font-semibold text-emergency")}>
                  {o.abnormal ? "ABNORMAL: " : ""}{o.result_text}
                </p>
              ) : null}
              <p className="mt-0.5 text-xs text-muted-foreground">
                ordered by {o.ordered_by} {clockTime(o.created_at)}
                {o.entered_by ? ` · result by ${o.entered_by}` : ""}
                {o.verified_by ? ` · verified by ${o.verified_by} ${clockTime(o.verified_at)}` : ""}
              </p>
            </li>
          ))}
        </ul>
      ) : <p className="text-sm text-muted-foreground">No investigations ordered.</p>}
    </Card>
  );
}

function Timeline({ e }: { e: Enc }) {
  return (
    <Card className="h-fit">
      <h2 className="mb-2 font-bold">Timeline</h2>
      <ol className="relative space-y-3 border-l border-border pl-4">
        {e.timeline.map((t, i) => (
          <li key={i} className="text-sm">
            <span className={cn("absolute -left-1.5 mt-1 h-3 w-3 rounded-full",
              t.kind === "state" ? "bg-primary" : t.kind === "correction" ? "bg-warning" : "bg-mint-strong")} />
            <div className="font-medium">{t.summary}</div>
            <div className="text-xs text-muted-foreground">
              {clockTime(t.at)} · {t.actor ?? "system"}{t.actor_role ? ` (${ROLE_LABEL[t.actor_role] ?? t.actor_role})` : ""}
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}
