"use client";

import { CheckCircle2, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError, type PatientKeysOut, type TriageOut } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { clearPending, getPending, refreshBundle } from "@/lib/offline";
import { getIdentity, saveIdentity, setPendingRecovery } from "@/lib/patient-store";

const STAFF = /^\/(hospital|admin|auth)/;

async function sendPending(): Promise<{ id: string; name: string } | null> {
  const p = await getPending();
  if (!p || !navigator.onLine) return null;
  if (!(await getIdentity())) {
    const k = await api<PatientKeysOut>("/patients/start", { body: {} });
    await saveIdentity({ patientId: k.patient_id, vitalisId: k.vitalis_id, deviceKey: k.device_key });
    setPendingRecovery(k.recovery_code);
  }
  const tri = await api<TriageOut>("/triage", { body: { taps: p.taps }, patient: true });
  let ref: { id: string };
  try {
    ref = await api<{ id: string }>(`/triage/${tri.report_id}/referral`, { body: { facility_id: p.facility_id }, patient: true });
  } catch (e) {
    // That hospital can no longer take her (closed, full, unverified): send to the best one available now.
    if (!(e instanceof ApiError)) throw e;
    ref = await api<{ id: string }>(`/triage/${tri.report_id}/referral`, { body: {}, patient: true });
  }
  await clearPending();
  return { id: ref.id, name: p.facility_name };
}

/** Keeps the offline copy fresh while online, and sends a request saved with no signal as soon as it can. */
export function OfflineSync() {
  const t = useT();
  const [sent, setSent] = useState<{ id: string; name: string } | null>(null);

  useEffect(() => {
    if (STAFF.test(window.location.pathname)) return;
    let busy = false;
    const run = async () => {
      if (busy || !navigator.onLine) return;
      busy = true;
      try {
        await refreshBundle();
        const r = await sendPending();
        if (r) setSent(r);
      } catch {
        /* still offline or the server is unreachable: try again on the next "online" */
      } finally {
        busy = false;
      }
    };
    void run();
    window.addEventListener("online", run);
    const every = window.setInterval(run, 15 * 60 * 1000);
    return () => {
      window.removeEventListener("online", run);
      window.clearInterval(every);
    };
  }, []);

  if (!sent) return null;
  return (
    <div className="fixed inset-x-3 bottom-3 z-50 mx-auto flex max-w-md items-center gap-3 rounded-2xl bg-primary p-4 text-primary-foreground shadow-lg"
      role="status">
      <CheckCircle2 className="h-6 w-6 shrink-0" />
      <p className="flex-1 font-semibold">{t("offline.sent").replace("{name}", sent.name)}</p>
      <Link href={`/referral/${sent.id}`} className="rounded-lg bg-white/15 px-3 py-2 font-bold" onClick={() => setSent(null)}>
        {t("offline.open")}
      </Link>
      <button type="button" aria-label="Close" onClick={() => setSent(null)}><X className="h-5 w-5" /></button>
    </div>
  );
}
