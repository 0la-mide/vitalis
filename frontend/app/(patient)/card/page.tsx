"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, ChevronLeft, Eye, FileText, QrCode, ShieldCheck, ShieldOff, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { RecoverySlip } from "@/components/triage/RecoverySlip";
import { Logo } from "@/components/staff/StaffShell";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/card";
import { inputCls } from "@/components/ui/field";
import { api, type PatientKeysOut, type Schemas } from "@/lib/api";
import { getIdentity, saveIdentity, setPendingRecovery } from "@/lib/patient-store";
import { cn } from "@/lib/utils";
import { vitalLabel } from "@/lib/vitals";

type Rec = Schemas["MyRecord"];
type Tab = "record" | "visits" | "share" | "access";
const fmt = (iso: string) => new Date(iso).toLocaleDateString([], { day: "numeric", month: "short", year: "numeric" });

/** The patient's own health record on their phone, and who they share it with. */
export default function MyRecordPage() {
  const [hasId, setHasId] = useState<boolean | null>(null);
  const [tab, setTab] = useState<Tab>("record");
  useEffect(() => {
    void getIdentity().then((i) => setHasId(!!i));
  }, []);

  return (
    <main className="mx-auto w-full max-w-md space-y-4 px-4 py-3">
      <div className="flex items-center justify-between">
        <Link href="/" aria-label="Back" className="inline-flex h-11 w-11 items-center justify-center rounded-full bg-muted"><ChevronLeft /></Link>
        <Logo subtitle="My health record" />
        <span className="w-11" />
      </div>
      {hasId === false ? <NoCard onRestored={() => setHasId(true)} /> : null}
      {hasId ? (
        <>
          <Requests />
          <div className="grid grid-cols-4 gap-1 rounded-lg bg-muted p-1 text-sm font-semibold">
            {([["record", "Record"], ["visits", "Visits"], ["share", "Share"], ["access", "Who looked"]] as const).map(([k, l]) => (
              <button key={k} type="button" onClick={() => setTab(k)}
                className={cn("min-h-11 rounded-md", tab === k ? "bg-card shadow-sm" : "text-muted-foreground")}>{l}</button>
            ))}
          </div>
          {tab === "record" ? <RecordTab /> : null}
          {tab === "visits" ? <VisitsTab /> : null}
          {tab === "share" ? <ShareTab /> : null}
          {tab === "access" ? <AccessTab /> : null}
          <RecoverySlip always />
        </>
      ) : null}
    </main>
  );
}

function useMyRecord() {
  return useQuery({ queryKey: ["my-record"], queryFn: () => api<Rec>("/me/records", { patient: true }) });
}

function Requests() {
  const qc = useQueryClient();
  const { data = [] } = useQuery({
    queryKey: ["my-requests"],
    queryFn: () => api<Schemas["RequestRow"][]>("/me/access-requests", { patient: true }),
    refetchInterval: 5000,
  });
  const decide = useMutation({
    mutationFn: (v: { id: string; decision: "allow" | "deny" }) =>
      api(`/me/access-requests/${v.id}`, { body: { decision: v.decision }, patient: true }),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ["my-requests"] });
      void qc.invalidateQueries({ queryKey: ["my-access"] });
    },
  });
  if (!data.length) return null;
  return (
    <div className="space-y-2">
      {data.map((r) => (
        <Card key={r.id} className="border-2 border-info/40 bg-info-soft">
          <div className="flex items-start gap-3">
            <BellRing className="mt-0.5 h-6 w-6 shrink-0 text-info" />
            <div className="flex-1">
              <p className="font-bold">{r.facility_name.replace(" (Demo)", "")} wants to see your health record</p>
              <p className="text-sm text-muted-foreground">Asked by {r.requested_by} · {r.purpose}</p>
              <p className="mt-1 text-sm">If you allow, they can see your visits and results from other hospitals for 24 hours. You can stop it any time.</p>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <Button variant="outline" size="lg" disabled={decide.isPending} onClick={() => decide.mutate({ id: r.id, decision: "deny" })}>Don&apos;t allow</Button>
            <Button size="lg" disabled={decide.isPending} onClick={() => decide.mutate({ id: r.id, decision: "allow" })}>Allow</Button>
          </div>
        </Card>
      ))}
    </div>
  );
}

function RecordTab() {
  const { data } = useMyRecord();
  if (!data) return <p className="text-muted-foreground">Loading…</p>;
  const by = (k: string) => data.history.filter((h) => (h as { kind: string }).kind === k) as { text: string; detail: string | null; source: string; recorded_at: string; onset_age: number | null }[];
  const allergies = by("allergy");
  return (
    <div className="space-y-3">
      <Card className="text-center">
        <p className="text-sm text-muted-foreground">Your VITALIS ID</p>
        <p className="font-mono text-3xl font-bold tracking-wider">{data.vitalis_id}</p>
      </Card>
      <Card className={cn(allergies.length && "border-l-4 border-l-emergency")}>
        <h2 className="font-bold">Allergies</h2>
        {allergies.length ? allergies.map((a, i) => (
          <p key={i} className="mt-1"><b>{a.text}</b>{a.detail ? ` · ${a.detail}` : ""}<span className="block text-xs text-muted-foreground">{a.source} · {fmt(a.recorded_at)}</span></p>
        )) : <p className="text-sm text-muted-foreground">None recorded.</p>}
      </Card>
      {([["condition", "Conditions"], ["medication", "Medicines"], ["family", "Family history"]] as const).map(([k, title]) => (
        <Card key={k}>
          <h2 className="font-bold">{title}</h2>
          {by(k).length ? by(k).map((h, i) => (
            <p key={i} className="mt-1">
              {k === "family" ? `${h.detail ?? "Relative"}: ${h.text}` : h.text}{k === "medication" && h.detail ? ` · ${h.detail}` : ""}
              <span className="block text-xs text-muted-foreground">{h.source} · {fmt(h.recorded_at)}</span>
            </p>
          )) : <p className="text-sm text-muted-foreground">None recorded.</p>}
        </Card>
      ))}
    </div>
  );
}

function VisitsTab() {
  const { data } = useMyRecord();
  if (!data) return <p className="text-muted-foreground">Loading…</p>;
  type Visit = { encounter_id: string; facility: string; date: string; complaint: string | null; disposition: string | null;
    vitals: { kind: string; value: number; unit: string }[]; results: { test: string; text: string; abnormal: boolean }[];
    notes: { body: string }[]; prescriptions: { drug: string; dose: string }[] };
  const visits = data.visits as Visit[];
  if (!visits.length) return <Card className="text-muted-foreground">No hospital visits yet.</Card>;
  return (
    <ol className="space-y-3">
      {visits.map((v) => {
        const latest = Object.values(Object.fromEntries(v.vitals.map((x) => [x.kind, x])));
        return (
          <li key={v.encounter_id}>
            <Card className="space-y-2">
              <div className="flex items-start justify-between gap-2">
                <div><p className="font-bold">{v.facility}</p><p className="text-sm text-muted-foreground">{fmt(v.date)}{v.complaint ? ` · ${v.complaint}` : ""}</p></div>
                {v.disposition ? <Badge>{v.disposition}</Badge> : null}
              </div>
              {latest.length ? <p className="text-sm">{latest.map((x) => `${vitalLabel(x.kind)} ${x.value}${x.unit === "%" ? "%" : ` ${x.unit}`}`).join(" · ")}</p> : null}
              {v.results.map((r, i) => <p key={i} className={cn("text-sm", r.abnormal && "font-semibold text-warning")}><FileText className="mr-1 inline h-3.5 w-3.5" />{r.test}: {r.text}</p>)}
              {v.prescriptions.map((p, i) => <p key={i} className="text-sm">💊 {p.drug} · {p.dose}</p>)}
              {v.notes.map((n, i) => <details key={i} className="text-sm"><summary className="cursor-pointer text-muted-foreground">Doctor&apos;s note</summary><p className="mt-1 whitespace-pre-wrap">{n.body}</p></details>)}
            </Card>
          </li>
        );
      })}
    </ol>
  );
}

function ShareTab() {
  const qc = useQueryClient();
  const { data: facilities = [] } = useQuery({
    queryKey: ["facilities-list"],
    queryFn: () => api<Schemas["HospitalCard"][]>("/facilities"),
    staleTime: 60000,
  });
  const [facility, setFacility] = useState("");
  const [scope, setScope] = useState<"full" | "summary">("full");
  const [share, setShare] = useState<Schemas["ShareOut"] | null>(null);
  const [left, setLeft] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!share) return;
    const tick = () => setLeft(Math.max(0, Math.round((new Date(share.expires_at).getTime() - Date.now()) / 1000)));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [share]);

  const make = async () => {
    setError(null);
    try {
      setShare(await api<Schemas["ShareOut"]>("/me/consents", { body: { facility_id: facility || null, scope }, patient: true }));
      void qc.invalidateQueries({ queryKey: ["my-access"] });
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const cancel = async () => {
    if (share) await api(`/me/consents/${share.consent_id}`, { method: "DELETE", patient: true }).catch(() => {});
    setShare(null);
    void qc.invalidateQueries({ queryKey: ["my-access"] });
  };

  if (share && left > 0) {
    return (
      <Card className="space-y-3 text-center">
        <p className="font-bold">Show this to the hospital</p>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={share.qr_png} alt="QR code to share your record" className="mx-auto w-64 rounded-md border border-border bg-white p-2" />
        <p className="text-sm text-muted-foreground">
          {share.facility_name ? `Only ${share.facility_name.replace(" (Demo)", "")}` : "Any verified hospital"} · works once ·{" "}
          <b className="tabular-nums text-foreground">{Math.floor(left / 60)}:{String(left % 60).padStart(2, "0")}</b> left
        </p>
        <p className="text-xs text-muted-foreground">They will see your record for 24 hours. You can stop it in &quot;Who looked&quot;.</p>
        <Button variant="outline" className="w-full" onClick={cancel}><X className="h-4 w-4" />Cancel this code</Button>
      </Card>
    );
  }
  return (
    <Card className="space-y-3">
      <div className="flex items-center gap-2 font-bold"><QrCode className="h-5 w-5 text-primary" />Share your record with a hospital</div>
      <p className="text-sm text-muted-foreground">Make a code the hospital scans. It works once and expires in 10 minutes.</p>
      <label className="grid gap-1 text-sm font-medium">Which hospital?
        <select value={facility} onChange={(e) => setFacility(e.target.value)} className={inputCls}>
          <option value="">Any verified hospital</option>
          {facilities.map((f) => <option key={f.facility_id} value={f.facility_id}>{f.name.replace(" (Demo)", "")}</option>)}
        </select>
      </label>
      <div className="grid grid-cols-2 gap-2">
        {([["full", "Everything", "Visits, results, notes, medicines"], ["summary", "Summary only", "Allergies, conditions, medicines"]] as const).map(([k, l, d]) => (
          <button key={k} type="button" onClick={() => setScope(k)}
            className={cn("rounded-lg border-2 p-3 text-left", scope === k ? "border-primary bg-mint" : "border-border")}>
            <span className="block font-semibold">{l}</span><span className="text-xs text-muted-foreground">{d}</span>
          </button>
        ))}
      </div>
      {error ? <p className="text-sm text-emergency">{error}</p> : null}
      <Button size="lg" className="w-full" onClick={make}><QrCode className="h-5 w-5" />Show my QR code</Button>
    </Card>
  );
}

function AccessTab() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["my-access"], queryFn: () => api<Schemas["AccessLog"]>("/me/access-log", { patient: true }), refetchInterval: 8000 });
  const revoke = useMutation({
    mutationFn: (id: string) => api(`/me/consents/${id}`, { method: "DELETE", patient: true }),
    onSettled: () => qc.invalidateQueries({ queryKey: ["my-access"] }),
  });
  if (!data) return <p className="text-muted-foreground">Loading…</p>;
  const active = data.consents.filter((c) => c.active);
  return (
    <div className="space-y-3">
      <Card>
        <h2 className="flex items-center gap-2 font-bold"><ShieldCheck className="h-5 w-5 text-primary" />Who can see your record now</h2>
        {active.length ? active.map((c) => (
          <div key={c.id} className="mt-2 flex items-center justify-between gap-2 rounded-md bg-muted p-2">
            <div className="text-sm">
              <b>{(c.facility_name ?? "Any verified hospital").replace(" (Demo)", "")}</b>
              <span className="block text-xs text-muted-foreground">{c.scope === "full" ? "Everything" : "Summary"} · until {new Date(c.expires_at).toLocaleString([], { hour: "2-digit", minute: "2-digit", day: "numeric", month: "short" })} · via {c.via.replace("_", " ")}</span>
            </div>
            <Button size="sm" variant="outline" disabled={revoke.isPending} onClick={() => revoke.mutate(c.id)}><ShieldOff className="h-4 w-4" />Stop</Button>
          </div>
        )) : <p className="mt-1 text-sm text-muted-foreground">Only the hospitals that treated you see what they recorded. Allergies are always shared with a hospital treating you, for your safety.</p>}
      </Card>
      <Card>
        <h2 className="flex items-center gap-2 font-bold"><Eye className="h-5 w-5 text-muted-foreground" />Who looked</h2>
        <ul className="mt-2 space-y-2">
          {data.events.map((e, i) => (
            <li key={i} className="text-sm">
              <b>{e.who ?? "Someone"}</b>{e.facility ? ` at ${e.facility.replace(" (Demo)", "")}` : ""} {e.what}
              <span className="block text-xs text-muted-foreground">{new Date(e.at).toLocaleString()}</span>
            </li>
          ))}
          {!data.events.length ? <li className="text-sm text-muted-foreground">Nobody has looked yet.</li> : null}
        </ul>
      </Card>
    </div>
  );
}

function NoCard({ onRestored }: { onRestored: () => void }) {
  const [vid, setVid] = useState("");
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  return (
    <Card className="space-y-2">
      <h2 className="font-bold">No VITALIS card on this phone yet</h2>
      <p className="text-sm text-muted-foreground">Enter the VITALIS ID and recovery code from your slip to open your record here.</p>
      <input className={cn(inputCls, "font-mono uppercase")} placeholder="VT-XXXX-XX" value={vid} onChange={(e) => setVid(e.target.value)} aria-label="VITALIS ID" />
      <input className={cn(inputCls, "font-mono uppercase")} placeholder="XXXX-XXXX-XXXX" value={code} onChange={(e) => setCode(e.target.value)} aria-label="Recovery code" />
      <Button size="lg" disabled={!vid || !code} onClick={async () => {
        try {
          const k = await api<PatientKeysOut>("/patients/recover", { body: { vitalis_id: vid, recovery_code: code } });
          await saveIdentity({ patientId: k.patient_id, vitalisId: k.vitalis_id, deviceKey: k.device_key });
          setPendingRecovery(k.recovery_code);
          onRestored();
        } catch (e) {
          setMsg((e as Error).message);
        }
      }}>Open my record</Button>
      {msg ? <p className="text-sm text-emergency">{msg}</p> : null}
    </Card>
  );
}
