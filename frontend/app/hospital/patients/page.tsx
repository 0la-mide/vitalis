"use client";

import { useQuery } from "@tanstack/react-query";
import { FlaskConical, Radio, Siren, UserPlus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useFacilityStream } from "@/components/hospital/useFacilityStream";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/card";
import { Field, inputCls } from "@/components/ui/field";
import { api, type Schemas } from "@/lib/api";
import { useMe } from "@/lib/staff";
import { cn, timeAgo } from "@/lib/utils";

type Item = Schemas["EncounterListItem"];

const COLUMNS: { states: string[]; title: string; roles: string[] }[] = [
  { states: ["registered", "awaiting_nursing"], title: "Nursing", roles: ["nurse"] },
  { states: ["awaiting_doctor", "results_ready"], title: "Doctor", roles: ["doctor"] },
  { states: ["awaiting_investigation"], title: "Investigations", roles: ["lab", "radiology"] },
  { states: ["awaiting_disposition"], title: "Discharge / admission", roles: ["receptionist"] },
];
const AGE: Record<string, string> = { under5: "Under 5", child: "Child", teen: "Teen", adult: "Adult", elderly: "Elderly" };

export default function PatientsBoard() {
  const { data: me } = useMe();
  const [showWalkIn, setShowWalkIn] = useState(false);
  const { data: items = [], isLoading } = useQuery({
    queryKey: ["encounters"],
    queryFn: () => api<Item[]>("/hospital/encounters"),
    refetchInterval: 30000,
  });
  const live = useFacilityStream([["encounters"]]);
  const canRegister = ["receptionist", "nurse", "facility_admin"].includes(me?.role ?? "");

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-bold">Patients in the facility</h1>
        <div className="flex items-center gap-3">
          <span className={cn("inline-flex items-center gap-1.5 text-sm", live ? "text-primary" : "text-muted-foreground")}>
            <Radio className={cn("h-4 w-4", live && "vt-pulse")} aria-hidden /> {live ? "Live" : "Connecting…"}
          </span>
          {canRegister ? (
            <Button variant={showWalkIn ? "mint" : "primary"} onClick={() => setShowWalkIn(!showWalkIn)}>
              <UserPlus className="h-4 w-4" /> Register walk-in
            </Button>
          ) : null}
        </div>
      </div>
      {showWalkIn ? <WalkInForm onDone={() => setShowWalkIn(false)} /> : null}
      {isLoading ? <p className="text-muted-foreground">Loading…</p> : null}
      <div className="grid gap-3 lg:grid-cols-4">
        {COLUMNS.map((col) => {
          const rows = items.filter((i) => col.states.includes(i.state));
          const mine = col.roles.includes(me?.role ?? "");
          return (
            <section key={col.title} className={cn("rounded-2xl bg-card/60 p-2", mine && "ring-2 ring-primary")}>
              <h2 className="flex items-center justify-between px-1 pb-2 text-sm font-bold uppercase text-muted-foreground">
                {col.title} <span className="rounded-full bg-muted px-2 text-xs">{rows.length}</span>
              </h2>
              <div className="grid gap-2">
                {rows.map((i) => <BoardCard key={i.id} i={i} />)}
                {!rows.length ? <p className="px-1 pb-2 text-sm text-muted-foreground">Nobody waiting</p> : null}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}

function BoardCard({ i }: { i: Item }) {
  return (
    <Link href={`/hospital/patients/${i.id}`}>
      <Card className={cn("space-y-1 p-3 hover:bg-muted", i.emergency && "border-l-4 border-l-emergency")}>
        <div className="flex items-center justify-between gap-2">
          <span className="font-mono font-semibold">{i.patient.vitalis_id}</span>
          {i.state === "results_ready" ? <Badge tone="ok">Results ready</Badge> : null}
        </div>
        <p className="text-xs text-muted-foreground">
          {AGE[i.patient.age_group ?? ""] ?? "?"} · {i.patient.sex ?? "?"}
          {i.patient.pregnant ? " · pregnant" : ""}
          {i.care_label ? ` · ${i.care_label}` : ""}
        </p>
        {i.headline ? (
          <p className={cn("line-clamp-2 text-sm", i.emergency && "font-semibold text-emergency")}>
            {i.emergency ? <Siren className="mr-1 inline h-3.5 w-3.5" aria-hidden /> : null}
            {i.headline}
          </p>
        ) : null}
        <p className="flex items-center gap-2 text-xs text-muted-foreground">
          in since {timeAgo(i.created_at)}
          {i.open_orders ? (
            <span className="inline-flex items-center gap-0.5"><FlaskConical className="h-3 w-3" /> {i.open_orders}</span>
          ) : null}
        </p>
      </Card>
    </Link>
  );
}

function WalkInForm({ onDone }: { onDone: () => void }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [slip, setSlip] = useState<Schemas["WalkInOut"] | null>(null);

  if (slip) {
    return (
      <Card className="border-2 border-dashed border-primary">
        <h2 className="font-bold">Walk-in registered — give the family this slip</h2>
        <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
          <dt className="text-sm text-muted-foreground">VITALIS ID</dt>
          <dd className="font-mono text-xl font-bold">{slip.vitalis_id}</dd>
          <dt className="text-sm text-muted-foreground">Recovery code</dt>
          <dd className="font-mono text-xl font-bold">{slip.recovery_code}</dd>
        </dl>
        <div className="mt-3 flex gap-2">
          <Button onClick={() => router.push(`/hospital/patients/${slip.encounter_id}`)}>Open encounter</Button>
          <Button variant="outline" onClick={onDone}>Done</Button>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <form
        className="grid gap-3 md:grid-cols-4"
        onSubmit={async (e) => {
          e.preventDefault();
          const fd = new FormData(e.currentTarget);
          setBusy(true);
          setError(null);
          try {
            const body = {
              age_group: fd.get("age_group"),
              sex: fd.get("sex"),
              pregnant: fd.get("pregnant") === "on",
              emergency: fd.get("emergency") === "on",
              chief_complaint: fd.get("chief_complaint"),
              ...(fd.get("family_phone") ? { family_phone: fd.get("family_phone") } : {}),
            };
            setSlip(await api<Schemas["WalkInOut"]>("/hospital/encounters", { body }));
          } catch (err) {
            setError((err as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <Field label="Age group">
          <select name="age_group" className={inputCls} defaultValue="adult">
            {Object.entries(AGE).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </Field>
        <Field label="Sex">
          <select name="sex" className={inputCls} defaultValue="unknown">
            <option value="female">Female</option>
            <option value="male">Male</option>
            <option value="unknown">Not recorded</option>
          </select>
        </Field>
        <Field label="Family phone (optional)"><input name="family_phone" type="tel" className={inputCls} /></Field>
        <div className="flex items-end gap-4 pb-2 text-sm">
          <label className="flex items-center gap-2"><input type="checkbox" name="pregnant" /> Pregnant</label>
          <label className="flex items-center gap-2 font-semibold text-emergency"><input type="checkbox" name="emergency" /> Emergency</label>
        </div>
        <Field label="Main complaint" className="md:col-span-3">
          <input name="chief_complaint" required minLength={2} className={inputCls} />
        </Field>
        <div className="flex items-end">
          <Button type="submit" className="w-full" disabled={busy}>{busy ? "Registering…" : "Register"}</Button>
        </div>
        {error ? <p className="text-sm text-emergency md:col-span-4">{error}</p> : null}
      </form>
    </Card>
  );
}
