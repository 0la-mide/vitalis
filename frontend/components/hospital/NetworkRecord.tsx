"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { Building2, Lock, QrCode, Send, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/card";
import { api, type Schemas } from "@/lib/api";
import { cn } from "@/lib/utils";
import { vitalLabel } from "@/lib/vitals";

type Visit = { encounter_id: string; facility: string; date: string; complaint: string | null; disposition: string | null;
  vitals: { kind: string; value: number; unit: string }[]; results: { test: string; text: string; abnormal: boolean }[];
  notes: { body: string }[]; prescriptions: { drug: string; dose: string }[] };

/** Visits at other hospitals: visible only when the patient has shared their record with this hospital. */
export function NetworkRecordCard({ patientId, encounterId }: { patientId: string; encounterId: string }) {
  const qc = useQueryClient();
  const statusKey = ["consent", patientId];
  const { data: st } = useQuery({
    queryKey: statusKey,
    queryFn: () => api<Schemas["ConsentStatus"]>(`/hospital/patients/${patientId}/consent`),
    refetchInterval: (q) => (q.state.data?.pending_request ? 3000 : 30000),
  });
  const { data: net } = useQuery({
    queryKey: ["network-record", patientId],
    queryFn: () => api<Schemas["NetworkRecord"]>(`/hospital/patients/${patientId}/network-record`),
    enabled: !!st?.active,
  });
  const ask = useMutation({
    mutationFn: () => api<Schemas["ConsentStatus"]>(`/hospital/patients/${patientId}/access-requests`, { body: { purpose: "Treatment at this hospital" } }),
    onSuccess: (d) => qc.setQueryData(statusKey, d),
  });
  // When the patient shares, history from other hospitals becomes visible in the record card too.
  const active = !!st?.active;
  useEffect(() => {
    if (active) void qc.invalidateQueries({ queryKey: ["record", encounterId] });
  }, [active, encounterId, qc]);

  if (!st) return null;
  if (!st.active) {
    return (
      <Card className="space-y-2">
        <h2 className="flex items-center gap-2 font-bold"><Lock className="h-4 w-4 text-muted-foreground" />Records from other hospitals</h2>
        <p className="text-sm text-muted-foreground">
          {st.other_hospital_visits
            ? `${st.other_hospital_visits} visit(s) at other hospitals${st.hidden_history ? ` and ${st.hidden_history} record entr${st.hidden_history === 1 ? "y" : "ies"}` : ""} are private until the patient shares them.`
            : "No visits at other hospitals on VITALIS."}{" "}
          Allergies are always shown.
        </p>
        {st.other_hospital_visits ? (
          <div className="flex flex-wrap items-center gap-2">
            {st.pending_request ? (
              <Badge tone="info"><Send className="h-3.5 w-3.5" />Waiting for the patient to tap Allow on their phone…</Badge>
            ) : (
              <Button variant="outline" disabled={ask.isPending} onClick={() => ask.mutate()}><Send className="h-4 w-4" />Ask the patient to share</Button>
            )}
            <span className="inline-flex items-center gap-1 text-sm text-muted-foreground"><QrCode className="h-4 w-4" />or scan the QR on their phone</span>
          </div>
        ) : null}
        {ask.error ? <p className="text-sm text-emergency">{(ask.error as Error).message}</p> : null}
      </Card>
    );
  }
  const visits = (net?.visits ?? []) as Visit[];
  return (
    <Card className="space-y-3 border-l-4 border-l-primary">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-bold"><Building2 className="h-4 w-4 text-muted-foreground" />Records from other hospitals</h2>
        <Badge tone="ok"><ShieldCheck className="h-3.5 w-3.5" />Patient consented · until {new Date(st.consent!.expires_at).toLocaleString([], { hour: "2-digit", minute: "2-digit", day: "numeric", month: "short" })}</Badge>
      </div>
      {st.consent?.scope === "summary" ? <p className="text-sm text-muted-foreground">The patient shared a summary only (allergies, conditions, medicines).</p> : null}
      <ol className="space-y-2">
        {visits.map((v) => {
          const latest = Object.values(Object.fromEntries(v.vitals.map((x) => [x.kind, x])));
          return (
            <li key={v.encounter_id} className="rounded-md border border-border p-3 text-sm">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <b>{v.facility}</b>
                <span className="text-xs text-muted-foreground">{new Date(v.date).toLocaleDateString()}</span>
              </div>
              {v.complaint ? <p className="text-muted-foreground">{v.complaint}</p> : null}
              {latest.length ? <p className="mt-1">{latest.map((x) => `${vitalLabel(x.kind)} ${x.value}`).join(" · ")}</p> : null}
              {v.results.map((r, i) => <p key={i} className={cn("mt-1", r.abnormal && "font-semibold text-warning")}>{r.test}: {r.text}</p>)}
              {v.prescriptions.map((p, i) => <p key={i} className="mt-1">Rx {p.drug} · {p.dose}</p>)}
              {v.notes.map((n, i) => <p key={i} className="mt-1 whitespace-pre-wrap text-muted-foreground">“{n.body}”</p>)}
            </li>
          );
        })}
        {net && !visits.length ? <li className="text-sm text-muted-foreground">No visits at other hospitals.</li> : null}
      </ol>
      <p className="text-xs text-muted-foreground">Every view is recorded and shown to the patient.</p>
    </Card>
  );
}
