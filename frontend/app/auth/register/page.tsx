"use client";

import { useQuery } from "@tanstack/react-query";
import { Building2, CheckCircle2, Pill, Stethoscope } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field, inputCls } from "@/components/ui/field";
import { api, type Schemas } from "@/lib/api";
import { cn } from "@/lib/utils";

type Kind = "facility" | "staff" | "worker";
type Options = {
  lgas: string[];
  services: { code: string; name: string }[];
  facility_types: string[];
  worker_types: string[];
  staff_roles: string[];
};

const KINDS: { kind: Kind; title: string; sub: string; icon: React.ReactNode }[] = [
  { kind: "facility", title: "Hospital or clinic", sub: "Register a facility and its admin", icon: <Building2 /> },
  { kind: "staff", title: "Hospital staff", sub: "Join a verified facility", icon: <Stethoscope /> },
  { kind: "worker", title: "Frontline worker", sub: "Chemist / PPMV, pharmacist, CHEW, midwife", icon: <Pill /> },
];

const LABEL: Record<string, string> = {
  teaching: "Teaching hospital",
  general: "General hospital",
  specialist: "Specialist hospital",
  clinic: "Clinic",
  phc: "Primary health centre",
  chemist: "Chemist / PPMV",
  pharmacist: "Pharmacist",
  chew: "CHEW",
  midwife: "Midwife",
  receptionist: "Receptionist",
  nurse: "Nurse",
  doctor: "Doctor",
  lab: "Lab / Radiology",
};

function DocInput() {
  return (
    <Field label="Licence document" hint="PDF, JPG or PNG, up to 5 MB. Only VITALIS reviewers can open it.">
      <input name="document" type="file" required accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
        className="text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-mint file:px-3 file:py-2 file:font-semibold" />
    </Field>
  );
}

function AccountFields() {
  return (
    <>
      <Field label="Full name"><input name="full_name" required minLength={2} className={inputCls} /></Field>
      <Field label="Email"><input name="email" type="email" required autoComplete="username" className={inputCls} /></Field>
      <Field label="Password" hint="At least 10 characters">
        <input name="password" type="password" required minLength={10} autoComplete="new-password" className={inputCls} />
      </Field>
      <Field label="Phone (optional)"><input name="phone" type="tel" className={inputCls} /></Field>
    </>
  );
}

export default function RegisterPage() {
  const [kind, setKind] = useState<Kind>("facility");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const { data: opts } = useQuery({ queryKey: ["reg-options"], queryFn: () => api<Options>("/auth/register/options") });
  const { data: facilities = [] } = useQuery({
    queryKey: ["reg-facilities"],
    queryFn: () => api<Schemas["FacilityOption"][]>("/auth/register/facilities"),
  });

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const fd = new FormData(e.currentTarget);
    if (!fd.get("phone")) fd.delete("phone");
    try {
      let res: Schemas["RegisteredOut"];
      if (kind === "staff") {
        res = await api("/auth/register/staff", { body: Object.fromEntries(fd.entries()) });
      } else {
        if (kind === "facility") fd.set("services", fd.getAll("svc").join(","));
        fd.delete("svc");
        res = await api(`/auth/register/${kind}`, { form: fd });
      }
      setDone(res.message);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    return (
      <main className="mx-auto w-full max-w-md px-4 py-12">
        <Card className="text-center">
          <CheckCircle2 className="mx-auto h-10 w-10 text-primary" />
          <h1 className="mt-2 text-xl font-bold">Registration received</h1>
          <p className="mt-1 text-muted-foreground">{done}</p>
          <p className="mt-3 text-sm">You can sign in now to follow your status. You will not see patient data until you are verified.</p>
          <Link href="/auth/login"><Button className="mt-4 w-full" size="lg">Go to sign in</Button></Link>
        </Card>
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-xl px-4 py-8">
      <h1 className="text-2xl font-bold">Join the VITALIS network</h1>
      <p className="text-sm text-muted-foreground">
        Everyone who sees patient data is registered and verified. Patients never register.
      </p>

      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        {KINDS.map((k) => (
          <button key={k.kind} type="button" onClick={() => { setKind(k.kind); setError(null); }}
            className={cn("flex flex-col items-start gap-1 rounded-xl border-2 p-3 text-left",
              kind === k.kind ? "border-primary bg-mint" : "border-border bg-card")}>
            <span className="text-primary [&_svg]:h-5 [&_svg]:w-5">{k.icon}</span>
            <span className="font-semibold">{k.title}</span>
            <span className="text-xs text-muted-foreground">{k.sub}</span>
          </button>
        ))}
      </div>

      <Card className="mt-4">
        <form key={kind} onSubmit={submit} className="grid gap-3">
          {kind === "facility" ? (
            <>
              <h2 className="font-bold">Facility</h2>
              <Field label="Facility name"><input name="facility_name" required className={inputCls} /></Field>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Type">
                  <select name="facility_type" required className={inputCls}>
                    {opts?.facility_types.map((t) => <option key={t} value={t}>{LABEL[t] ?? t}</option>)}
                  </select>
                </Field>
                <Field label="LGA">
                  <select name="lga" required className={inputCls}>
                    {opts?.lgas.map((l) => <option key={l}>{l}</option>)}
                  </select>
                </Field>
              </div>
              <Field label="Address"><input name="address" required className={inputCls} /></Field>
              <div className="grid gap-3 sm:grid-cols-3">
                <Field label="Facility phone"><input name="facility_phone" required className={inputCls} /></Field>
                <Field label="Latitude"><input name="lat" required inputMode="decimal" defaultValue="7.1475" className={inputCls} /></Field>
                <Field label="Longitude"><input name="lng" required inputMode="decimal" defaultValue="3.3619" className={inputCls} /></Field>
              </div>
              <Field label="Facility licence number"><input name="facility_licence_number" required className={inputCls} /></Field>
              <fieldset className="grid gap-1">
                <legend className="text-sm font-medium">Services you offer</legend>
                <div className="grid grid-cols-2 gap-1.5 text-sm">
                  {opts?.services.map((s) => (
                    <label key={s.code} className="flex items-center gap-2 rounded-lg bg-muted px-2 py-1.5">
                      <input type="checkbox" name="svc" value={s.code} /> {s.name}
                    </label>
                  ))}
                </div>
                <span className="text-xs text-muted-foreground">Availability starts as Unknown; your staff confirm it with one tap.</span>
              </fieldset>
              <DocInput />
              <h2 className="pt-2 font-bold">Facility admin account</h2>
              <AccountFields />
            </>
          ) : kind === "staff" ? (
            <>
              <Field label="Facility" hint="Only verified facilities are listed. Your facility admin approves you.">
                <select name="facility_id" required className={inputCls}>
                  {facilities.map((f) => <option key={f.id} value={f.id}>{f.name} — {f.lga}</option>)}
                </select>
              </Field>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Role">
                  <select name="role" required className={inputCls}>
                    {opts?.staff_roles.map((r) => <option key={r} value={r}>{LABEL[r] ?? r}</option>)}
                  </select>
                </Field>
                <Field label="Professional licence number" hint="e.g. MDCN, NMCN, MLSCN">
                  <input name="licence_number" required minLength={3} className={inputCls} />
                </Field>
              </div>
              <AccountFields />
            </>
          ) : (
            <>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Worker type">
                  <select name="worker_type" required className={inputCls}>
                    {opts?.worker_types.map((w) => <option key={w} value={w}>{LABEL[w] ?? w}</option>)}
                  </select>
                </Field>
                <Field label="Licence number" hint="e.g. PCN or PPMV">
                  <input name="licence_number" required minLength={3} className={inputCls} />
                </Field>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Shop / business name (optional)"><input name="business_name" className={inputCls} /></Field>
                <Field label="LGA">
                  <select name="lga" required className={inputCls}>
                    {opts?.lgas.map((l) => <option key={l}>{l}</option>)}
                  </select>
                </Field>
              </div>
              <DocInput />
              <AccountFields />
            </>
          )}
          {error ? <p className="rounded-lg bg-emergency-soft p-2 text-sm text-emergency">{error}</p> : null}
          <Button type="submit" size="lg" disabled={busy}>{busy ? "Submitting…" : "Submit for verification"}</Button>
        </form>
      </Card>
      <p className="mt-4 text-center text-sm text-muted-foreground">
        Already registered? <Link href="/auth/login" className="underline">Sign in</Link>
      </p>
    </main>
  );
}
