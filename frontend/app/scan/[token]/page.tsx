"use client";

import { CheckCircle2, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Logo } from "@/components/staff/StaffShell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, ApiError, type Schemas } from "@/lib/api";

/** Where a patient's QR leads. Staff only: redeems the single-use code for this hospital, then opens the patient. */
export default function ScanPage() {
  const { token } = useParams<{ token: string }>();
  const router = useRouter();
  const [state, setState] = useState<{ kind: "busy" } | { kind: "ok"; out: Schemas["RedeemOut"] } | { kind: "error"; msg: string; login?: boolean }>({ kind: "busy" });
  const once = useRef(false);

  useEffect(() => {
    if (once.current) return;
    once.current = true;
    api<Schemas["RedeemOut"]>("/qr/redeem", { body: { token } })
      .then((out) => {
        setState({ kind: "ok", out });
        if (out.encounter_id) setTimeout(() => router.replace(`/hospital/patients/${out.encounter_id}`), 1200);
      })
      .catch((e: ApiError) => setState({ kind: "error", msg: e.message, login: e.status === 401 }));
  }, [token, router]);

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-4 px-4 py-10">
      <Logo subtitle="Shared record" />
      {state.kind === "busy" ? <Card>Checking the patient&apos;s code…</Card> : null}
      {state.kind === "ok" ? (
        <Card className="space-y-2 border-l-4 border-l-primary">
          <p className="flex items-center gap-2 font-bold"><CheckCircle2 className="h-5 w-5 text-primary" />Record shared with your hospital</p>
          <p>Patient <span className="font-mono font-bold">{state.out.vitalis_id}</span> consented
            ({state.out.consent.scope === "full" ? "everything" : "summary only"}) until{" "}
            {new Date(state.out.consent.expires_at).toLocaleString([], { hour: "2-digit", minute: "2-digit", day: "numeric", month: "short" })}.</p>
          {state.out.encounter_id ? <p className="text-sm text-muted-foreground">Opening their visit…</p> : (
            <p className="text-sm text-muted-foreground">There is no open visit for this patient here yet. Register them at reception and the shared record will appear on their visit.</p>
          )}
          <Link href="/hospital/patients"><Button className="w-full">Patients in the facility</Button></Link>
        </Card>
      ) : null}
      {state.kind === "error" ? (
        <Card className="space-y-2 border-l-4 border-l-emergency">
          <p className="flex items-center gap-2 font-bold"><ShieldAlert className="h-5 w-5 text-emergency" />{state.login ? "Staff sign-in needed" : "Code not accepted"}</p>
          <p>{state.login ? "Only verified hospital staff can open a patient's shared record." : state.msg}</p>
          {state.login ? <Link href={`/auth/login?next=/scan/${token}`}><Button className="w-full">Sign in</Button></Link> : null}
        </Card>
      ) : null}
    </main>
  );
}
