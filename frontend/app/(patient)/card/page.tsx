"use client";

import Link from "next/link";
import { useState } from "react";
import { RecoverySlip } from "@/components/triage/RecoverySlip";
import { StepHeader } from "@/components/triage/shared";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api, type PatientKeysOut } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { saveIdentity, setPendingRecovery } from "@/lib/patient-store";

/** VITALIS card + restore on a new phone. Records/QR sharing come in Phase 8. */
export default function CardPage() {
  const t = useT();
  const [vid, setVid] = useState("");
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  const recover = async () => {
    setMsg(null);
    try {
      const k = await api<PatientKeysOut>("/patients/recover", { body: { vitalis_id: vid, recovery_code: code } });
      await saveIdentity({ patientId: k.patient_id, vitalisId: k.vitalis_id, deviceKey: k.device_key });
      setPendingRecovery(k.recovery_code);
      setNonce((n) => n + 1);
      setMsg("Restored on this phone. Save your NEW recovery code below.");
    } catch (e) {
      setMsg((e as Error).message);
    }
  };

  return (
    <main className="mx-auto w-full max-w-md space-y-4 px-4 py-2">
      <StepHeader title={t("slip.title")} audio="slip_title" />
      <RecoverySlip key={nonce} always />
      <Card>
        <h2 className="font-bold">Restore on this phone</h2>
        <div className="mt-2 grid gap-2">
          <input
            className="min-h-12 rounded-lg border border-border bg-card px-3 font-mono uppercase"
            placeholder="VT-XXXX-XX"
            value={vid}
            onChange={(e) => setVid(e.target.value)}
            aria-label="VITALIS ID"
          />
          <input
            className="min-h-12 rounded-lg border border-border bg-card px-3 font-mono uppercase"
            placeholder="XXXX-XXXX-XXXX"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            aria-label={t("slip.code")}
          />
          <Button size="lg" onClick={recover} disabled={!vid || !code}>
            Restore
          </Button>
          {msg ? <p className="text-sm">{msg}</p> : null}
        </div>
      </Card>
      <Link href="/" className="block py-3 text-center text-sm text-muted-foreground">
        ← {t("common.back")}
      </Link>
    </main>
  );
}
