"use client";

import { CheckCircle2, CircleAlert, Phone } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/card";
import type { HospitalCard, TriageOut } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { FreshnessBadge } from "./shared";

export function HospitalCardView({
  h,
  primary,
  onRequest,
  requesting,
  emergency,
}: {
  h: HospitalCard;
  primary?: boolean;
  onRequest?: () => void;
  requesting?: boolean;
  emergency?: boolean;
}) {
  const t = useT();
  return (
    <Card className={primary ? "border-2 border-primary" : ""}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-lg font-bold leading-snug">{h.name}</h3>
          <p className="text-sm text-muted-foreground">
            {h.distance_km} {t("hospital.km")} · ~{h.eta_minutes} {t("hospital.minutes")} ({t("hospital.estimate")})
          </p>
        </div>
        {h.ready_now ? (
          <Badge tone="ok">
            <CheckCircle2 className="h-3.5 w-3.5" /> {t("hospital.ready")}
          </Badge>
        ) : null}
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        <FreshnessBadge f={h.freshness} at={h.last_confirmed_at} />
        {h.warnings.slice(0, 2).map((w) => (
          <Badge key={w} tone="warn">
            <CircleAlert className="h-3.5 w-3.5" /> {w}
          </Badge>
        ))}
      </div>
      {primary && h.reasons.length ? (
        <ul className="mt-2 space-y-0.5 text-sm text-muted-foreground">
          {h.reasons.map((r) => (
            <li key={r}>✓ {r}</li>
          ))}
        </ul>
      ) : null}
      {onRequest ? (
        <div className="mt-3 flex gap-2">
          <Button
            size={primary ? "xl" : "lg"}
            variant={emergency && primary ? "calm" : "primary"}
            className="flex-1"
            onClick={onRequest}
            disabled={requesting}
          >
            {requesting ? t("common.loading") : t("results.request")}
          </Button>
          {h.phone ? (
            <a
              href={`tel:${h.phone.replace(/\s/g, "")}`}
              className="inline-flex min-h-14 w-14 items-center justify-center rounded-xl border-2 border-border"
              aria-label={`${t("referral.call")} ${h.name}`}
            >
              <Phone className="h-6 w-6" />
            </a>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}

export function ExcludedList({ result }: { result: TriageOut }) {
  const t = useT();
  const ex = result.hospitals.excluded;
  if (!ex.length) return null;
  return (
    <details className="rounded-xl bg-muted p-3 text-sm">
      <summary className="cursor-pointer font-semibold">
        {t("results.not_suitable")} ({ex.length})
      </summary>
      <ul className="mt-2 space-y-1">
        {ex.map((e) => (
          <li key={e.facility_id}>
            <b>{e.name}</b> · {e.distance_km} km — {e.reasons.join("; ")}
          </li>
        ))}
      </ul>
    </details>
  );
}
