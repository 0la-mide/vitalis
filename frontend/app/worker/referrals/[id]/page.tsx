"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Loader2, Navigation, Phone, Printer, Siren } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { stopDevTimer, DevTimer } from "@/components/triage/shared";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useTriage } from "@/lib/triage-store";
import { clockTime, cn } from "@/lib/utils";
import { STATUS, useWorkerReferrals, type WorkerReferral } from "@/components/worker/referrals";

const HospitalMap = dynamic(() => import("@/components/triage/HospitalMap"), { ssr: false });

export default function WorkerReferralPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  useWorkerReferrals(); // keeps the live stream open; invalidates this referral on events
  const { data: r, error } = useQuery({
    queryKey: ["worker-referral", id],
    queryFn: () => api<WorkerReferral>(`/worker/referrals/${id}`),
    refetchInterval: 10000,
  });
  const walkIn = useTriage((s) => s.walkIn);

  useEffect(() => {
    if (r?.status === "declined" && r.next_referral_id) {
      const t = setTimeout(() => router.replace(`/worker/referrals/${r.next_referral_id}`), 1500);
      return () => clearTimeout(t);
    }
    if (r?.status === "accepted") stopDevTimer();
  }, [r, router]);

  if (error) return <main className="p-6 text-center">{(error as Error).message}</main>;
  if (!r) return <main className="p-6 text-center text-muted-foreground">Loading…</main>;

  const slip = walkIn && walkIn.vitalisId === r.vitalis_id ? walkIn : null;
  const waiting = r.status === "pending" || r.status === "more_info" || (r.status === "declined" && !!r.next_referral_id);
  const good = r.status === "accepted" || r.status === "arrived" || r.status === "completed";

  return (
    <main className="mx-auto w-full max-w-md space-y-3 px-4 py-4">
      <DevTimer />
      {r.previous_facility_name && r.status === "pending" ? (
        <p className="rounded-xl bg-muted p-3 text-sm">{r.previous_facility_name} declined. Sent on to the next hospital.</p>
      ) : null}
      <Card className={cn("space-y-2", good && "border-2 border-primary", r.status === "overdue" && "border-2 border-emergency")}>
        <div className="flex items-start gap-2">
          {waiting ? <Loader2 className="mt-0.5 h-6 w-6 animate-spin text-primary" /> : good ?
            <CheckCircle2 className="mt-0.5 h-6 w-6 text-primary" /> : <Siren className="mt-0.5 h-6 w-6 text-emergency" />}
          <div className="flex-1">
            <Badge tone={STATUS[r.status]?.tone ?? "neutral"}>{STATUS[r.status]?.label ?? r.status}</Badge>
            <h1 className="mt-1 text-xl font-bold leading-snug">{r.facility_name}</h1>
            <p className="text-sm text-muted-foreground">
              {r.distance_km} km · ~{r.eta_minutes} min (estimate) · {r.care_label ?? r.care_type}
            </p>
          </div>
        </div>
        {r.red_flag_message ? (
          <p className="rounded-lg bg-emergency-soft p-2 text-sm font-semibold text-emergency">{r.red_flag_message}</p>
        ) : null}
        {r.decision_reason && r.status !== "accepted" ? (
          <p className="text-sm">Hospital note: {r.decision_reason}</p>
        ) : null}
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 text-sm">
          <dt className="text-muted-foreground">Sent</dt><dd>{clockTime(r.created_at)}</dd>
          {r.accepted_at ? (<><dt className="text-muted-foreground">Accepted</dt><dd>{clockTime(r.accepted_at)}</dd></>) : null}
          {r.arrived_at ? (<><dt className="text-muted-foreground">Arrived</dt><dd>{clockTime(r.arrived_at)}</dd></>) : null}
          {r.overdue_at ? (<><dt className="text-muted-foreground">Overdue</dt><dd>{clockTime(r.overdue_at)}</dd></>) : null}
        </dl>
        <div className="grid grid-cols-2 gap-2">
          <a href={r.directions_url} target="_blank" rel="noreferrer"
            className="flex min-h-12 items-center justify-center gap-1.5 rounded-xl bg-primary font-semibold text-primary-foreground">
            <Navigation className="h-4 w-4" /> Directions
          </a>
          {r.facility_phone ? (
            <a href={`tel:${r.facility_phone.replace(/\s/g, "")}`}
              className="flex min-h-12 items-center justify-center gap-1.5 rounded-xl border-2 border-border font-semibold">
              <Phone className="h-4 w-4" /> Call hospital
            </a>
          ) : null}
        </div>
      </Card>

      {/* Recovery slip handed to the family. Shown once, on this device, right after the walk-in. */}
      {slip ? (
        <Card className="print-slip border-2 border-dashed border-primary">
          <div className="flex items-center justify-between">
            <h2 className="font-bold">Hand this to the family</h2>
            <Button size="sm" variant="outline" className="print:hidden" onClick={() => window.print()}>
              <Printer className="h-4 w-4" /> Print
            </Button>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Write it down or print it. With these they can see their records on their own phone (VITALIS → My VITALIS card →
            Restore). The code works once.
          </p>
          <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
            <dt className="text-sm text-muted-foreground">VITALIS ID</dt>
            <dd className="font-mono text-xl font-bold">{slip.vitalisId}</dd>
            <dt className="text-sm text-muted-foreground">Recovery code</dt>
            <dd className="font-mono text-xl font-bold">{slip.recoveryCode}</dd>
            <dt className="text-sm text-muted-foreground">Hospital</dt>
            <dd className="text-sm">{r.facility_name}</dd>
          </dl>
        </Card>
      ) : (
        <Card className="text-center">
          <p className="text-sm text-muted-foreground">VITALIS ID</p>
          <p className="font-mono text-2xl font-bold">{r.vitalis_id}</p>
        </Card>
      )}

      <HospitalMap points={[{ id: r.facility_id, name: r.facility_name, lat: r.facility_lat, lng: r.facility_lng, highlight: true }]} />

      <div className="grid grid-cols-2 gap-2 pb-4 print:hidden">
        <Link href="/worker/referrals"><Button variant="outline" className="w-full">My referrals</Button></Link>
        <Link href="/worker"><Button className="w-full">New walk-in</Button></Link>
      </div>
    </main>
  );
}
