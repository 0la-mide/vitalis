"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock, Hospital, Loader2, Navigation, Phone, Siren } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { DevTimer, SpeakButton, stopDevTimer } from "@/components/triage/shared";
import { RecoverySlip } from "@/components/triage/RecoverySlip";
import { Card } from "@/components/ui/card";
import { api, type ReferralPatientOut } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { subscribe } from "@/lib/sse";
import { cn } from "@/lib/utils";

const HospitalMap = dynamic(() => import("@/components/triage/HospitalMap"), { ssr: false });

export default function ReferralPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const t = useT();
  const qc = useQueryClient();
  const { data: ref, error } = useQuery({
    queryKey: ["referral", id],
    queryFn: () => api<ReferralPatientOut>(`/referrals/${id}`, { patient: true }),
    refetchInterval: (q) => (q.state.error ? false : 10000), // safety net if the live stream drops
    retry: false,
  });

  // Live updates: any event on this triage report refetches the referral.
  useEffect(() => {
    return subscribe(
      `/referrals/${id}/stream`,
      (e) => {
        if (e.event !== "ready" && e.event !== "error") void qc.invalidateQueries({ queryKey: ["referral", id] });
      },
      { patient: true },
    );
  }, [id, qc]);

  // Declined -> follow to the next facility automatically.
  useEffect(() => {
    if (ref?.status === "declined" && ref.next_referral_id) {
      const tmr = setTimeout(() => router.replace(`/referral/${ref.next_referral_id}`), 1200);
      return () => clearTimeout(tmr);
    }
    if (ref?.status === "accepted") stopDevTimer();
  }, [ref, router]);

  if (error) {
    return (
      <main className="mx-auto max-w-md space-y-4 p-6 text-center">
        <p>{(error as Error).message}</p>
        <Link href="/" className="inline-block rounded-xl bg-primary px-4 py-3 font-semibold text-primary-foreground">VITALIS</Link>
      </main>
    );
  }
  if (!ref) {
    return <main className="p-6 text-center text-muted-foreground">{t("common.loading")}</main>;
  }

  const f = ref.facility;
  const status = ref.status;
  const headline =
    status === "accepted"
      ? t("referral.accepted")
      : status === "declined"
        ? ref.next_referral_id
          ? t("referral.declined_moving")
          : t("referral.none")
        : status === "more_info"
          ? t("referral.more_info")
          : status === "arrived" || status === "completed"
            ? t("referral.arrived")
            : status === "overdue"
              ? t("referral.overdue")
              : t("referral.waiting");
  const tone =
    status === "accepted" || status === "arrived" || status === "completed"
      ? "bg-primary text-primary-foreground"
      : status === "overdue" || (status === "declined" && !ref.next_referral_id)
        ? "bg-calm text-calm-foreground"
        : "bg-mint text-foreground";

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col gap-3 px-4 py-4">
      <DevTimer />
      {ref.previous_facility_name && status === "pending" ? (
        <p className="rounded-xl bg-muted p-3 text-sm">
          {ref.previous_facility_name}: ✗ · {t("referral.declined_moving")}
        </p>
      ) : null}

      <div className={cn("rounded-2xl p-5", tone)} role="status" aria-live="assertive">
        <div className="flex items-start gap-3">
          {status === "pending" || status === "more_info" || (status === "declined" && ref.next_referral_id) ? (
            <Loader2 className="mt-1 h-7 w-7 shrink-0 animate-spin" aria-hidden />
          ) : status === "accepted" || status === "arrived" ? (
            <CheckCircle2 className="mt-1 h-7 w-7 shrink-0" aria-hidden />
          ) : (
            <Siren className="mt-1 h-7 w-7 shrink-0" aria-hidden />
          )}
          <p className="flex-1 text-2xl font-bold leading-snug">{headline}</p>
          <SpeakButton code={`referral_${status}`} text={headline} className="bg-white/20 text-current" />
        </div>
        <div className="mt-3 flex items-center gap-2 text-lg font-semibold">
          <Hospital className="h-5 w-5" aria-hidden /> {f.name}
        </div>
        <div className="mt-1 flex items-center gap-2 opacity-90">
          <Clock className="h-4 w-4" aria-hidden /> ~{ref.eta_minutes} {t("hospital.minutes")} · {ref.distance_km}{" "}
          {t("hospital.km")} ({t("hospital.estimate")})
        </div>
      </div>

      {status === "accepted" || status === "overdue" ? (
        <div className="grid grid-cols-2 gap-3">
          <a
            href={ref.directions_url}
            target="_blank"
            rel="noreferrer"
            className="flex min-h-16 items-center justify-center gap-2 rounded-2xl bg-primary text-lg font-bold text-primary-foreground"
          >
            <Navigation className="h-5 w-5" aria-hidden /> {t("referral.directions")}
          </a>
          {f.phone ? (
            <a
              href={`tel:${f.phone.replace(/\s/g, "")}`}
              className="flex min-h-16 items-center justify-center gap-2 rounded-2xl border-2 border-border text-lg font-bold"
            >
              <Phone className="h-5 w-5" aria-hidden /> {t("referral.call")}
            </a>
          ) : null}
        </div>
      ) : null}

      {(status === "declined" && !ref.next_referral_id) || status === "overdue" ? (
        <a
          href="tel:112"
          className="flex min-h-16 items-center justify-center rounded-2xl border-2 border-emergency bg-card text-xl font-bold text-emergency"
        >
          {t("emergency.call")}
        </a>
      ) : null}

      <Card className="text-center">
        <p className="text-sm text-muted-foreground">{t("referral.show_id")}</p>
        <p className="mt-1 font-mono text-3xl font-bold tracking-wider">{ref.vitalis_id}</p>
      </Card>

      {status === "accepted" && ref.what_to_bring.length ? (
        <Card>
          <p className="font-semibold">{t("referral.bring")}</p>
          <ul className="mt-1 list-disc pl-5">
            {ref.what_to_bring.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </Card>
      ) : null}

      <HospitalMap points={[{ id: f.id, name: f.name, lat: f.lat, lng: f.lng, highlight: true }]} />

      <RecoverySlip />

      <Link href="/" className="py-3 text-center text-sm text-muted-foreground underline-offset-4 hover:underline">
        VITALIS
      </Link>
    </main>
  );
}
