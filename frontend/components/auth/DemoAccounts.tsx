"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Clock3, Pill, ShieldCheck, Smartphone } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { inputCls } from "@/components/ui/field";
import { api, type MeOut, type Schemas } from "@/lib/api";
import { saveIdentity } from "@/lib/patient-store";

type Accounts = Schemas["DemoAccounts"];
type Staff = Schemas["DemoStaff"];

const ROLES: { role: string; label: string }[] = [
  { role: "receptionist", label: "Reception" },
  { role: "nurse", label: "Nurse" },
  { role: "doctor", label: "Doctor" },
  { role: "lab", label: "Lab" },
  { role: "facility_admin", label: "Admin" },
];
const DEFAULT_HOSPITAL = "Abeokuta Central Hospital (Demo)";

/** Seeded demo accounts. The server returns 404 unless demo logins are enabled, and then this renders nothing. */
export function useDemoAccounts() {
  return useQuery({
    queryKey: ["demo-accounts"],
    queryFn: () => api<Accounts>("/demo/accounts"),
    retry: false,
    staleTime: 60_000,
  });
}

/** One tap into any demo role: for judges and teammates, so nobody types a password during the pitch. */
export function DemoAccounts({ onSignedIn }: { onSignedIn: (me: MeOut) => void }) {
  const qc = useQueryClient();
  const { data } = useDemoAccounts();
  const [hospital, setHospital] = useState(DEFAULT_HOSPITAL);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  if (!data?.staff.length) return null;

  const approved = data.staff.filter((s) => s.status === "approved");
  const hospitals = [...new Set(approved.filter((s) => s.facility).map((s) => s.facility as string))].sort();
  const at = (role: string) => approved.find((s) => s.facility === hospital && s.role === role);
  const admin = approved.find((s) => s.role === "network_admin");
  const workers = approved.filter((s) => s.role === "worker");
  const pending = data.staff.filter((s) => s.status !== "approved");

  const go = async (s: Staff) => {
    setBusy(s.email);
    setError(null);
    try {
      const me = await api<MeOut>("/demo/login", { body: { email: s.email } });
      qc.clear();
      qc.setQueryData(["me"], me);
      onSignedIn(me);
    } catch (e) {
      setError((e as Error).message);
      setBusy(null);
    }
  };
  const btn = (s: Staff | undefined, label: string, icon?: React.ReactNode) =>
    s ? (
      <Button key={s.email} size="sm" variant="outline" disabled={!!busy} onClick={() => go(s)} title={s.email}>
        {icon}{busy === s.email ? "Signing in…" : label}
      </Button>
    ) : null;

  return (
    <Card className="mt-4 space-y-3">
      <div>
        <h2 className="font-bold">Demo accounts</h2>
        <p className="text-sm text-muted-foreground">One tap, no password. Synthetic data only.</p>
      </div>
      <div className="space-y-2">
        <select value={hospital} onChange={(e) => setHospital(e.target.value)} className={inputCls} aria-label="Hospital">
          {hospitals.map((h) => <option key={h} value={h}>{h.replace(" (Demo)", "")}</option>)}
        </select>
        <div className="flex flex-wrap gap-2">
          {ROLES.map((r) => btn(at(r.role), r.label))}
        </div>
      </div>
      <div className="flex flex-wrap gap-2 border-t border-border pt-3">
        {btn(admin, "Network admin", <ShieldCheck className="size-4" />)}
        {workers.map((w, i) => btn(w, `Chemist ${i + 1}`, <Pill className="size-4" />))}
      </div>
      {pending.length ? (
        <details className="text-sm">
          <summary className="cursor-pointer text-muted-foreground">Pending accounts (verification demo)</summary>
          <div className="mt-2 flex flex-wrap gap-2">
            {pending.map((s) => btn(s, `${s.facility ? s.facility.replace(" (Demo)", "") + " · " : ""}${s.role.replace("_", " ")}`, <Clock3 className="size-4" />))}
          </div>
        </details>
      ) : null}
      {error ? <p className="text-sm text-emergency">{error}</p> : null}
    </Card>
  );
}

/** On the patient's record page: open a demo patient's record on this phone in one tap. */
export function DemoPatients({ onOpened }: { onOpened: () => void }) {
  const { data } = useDemoAccounts();
  const [busy, setBusy] = useState<string | null>(null);
  if (!data?.patients.length) return null;
  return (
    <div className="space-y-2 border-t border-border pt-3">
      <p className="text-sm font-semibold">Demo: open a patient&apos;s phone</p>
      <div className="flex flex-wrap gap-2">
        {data.patients.map((p) => (
          <Button key={p.vitalis_id} size="sm" variant="outline" disabled={!!busy} onClick={async () => {
            setBusy(p.vitalis_id);
            try {
              const k = await api<Schemas["DemoPatientOut"]>("/demo/patient", { body: { vitalis_id: p.vitalis_id } });
              await saveIdentity({ patientId: k.patient_id, vitalisId: k.vitalis_id, deviceKey: k.device_key });
              onOpened();
            } finally {
              setBusy(null);
            }
          }}>
            <Smartphone className="size-4" />{p.name.replace(" (demo)", "")}
          </Button>
        ))}
      </div>
    </div>
  );
}
