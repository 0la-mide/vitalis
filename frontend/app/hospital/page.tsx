"use client";

import { AlertsButton } from "@/components/ui/AlertsButton";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, CheckCircle2, Clock, Radio, Siren, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/card";
import { api, type IncomingItem } from "@/lib/api";
import { subscribe } from "@/lib/sse";
import { useMe } from "@/lib/staff";
import { clockTime, cn, timeAgo } from "@/lib/utils";

const DECIDERS = ["doctor", "nurse", "facility_admin"];
const FRONT_DESK = ["receptionist", "nurse", "facility_admin"];
const DECLINE_REASONS = ["No bed available", "Theatre busy", "Specialist not on duty", "No blood available"];

const STATUS_TONE: Record<string, "ok" | "warn" | "danger" | "neutral" | "info"> = {
  pending: "warn",
  more_info: "warn",
  accepted: "ok",
  arrived: "info",
  completed: "neutral",
  declined: "neutral",
  cancelled: "neutral",
  overdue: "danger",
  sent: "danger",
  ready: "ok",
};

const AGE: Record<string, string> = { under5: "Under 5", child: "Child 5–12", teen: "Teen", adult: "Adult", elderly: "Elderly" };

export default function IncomingPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const { data: me } = useMe();
  const [live, setLive] = useState(false);
  const [fresh, setFresh] = useState<Set<string>>(new Set());
  const known = useRef<Set<string> | null>(null);

  const { data: items = [], isLoading } = useQuery({
    queryKey: ["incoming"],
    queryFn: () => api<IncomingItem[]>("/hospital/incoming"),
    refetchInterval: 30000,
  });
  const { data: careLabels = {} } = useQuery({
    queryKey: ["care-types"],
    queryFn: () => api<Record<string, string>>("/hospital/care-types"),
    staleTime: Infinity,
  });

  // Highlight anything that appears after the first load.
  useEffect(() => {
    const ids = new Set(items.map((i) => `${i.id}:${i.status}`));
    if (known.current) {
      const added = [...ids].filter((x) => !known.current!.has(x)).map((x) => x.split(":")[0]);
      if (added.length) {
        setFresh(new Set(added));
        const tmr = setTimeout(() => setFresh(new Set()), 2600);
        known.current = ids;
        return () => clearTimeout(tmr);
      }
    }
    known.current = ids;
  }, [items]);

  useEffect(
    () =>
      subscribe("/hospital/stream", (e) => {
        if (e.event === "ready") setLive(true);
        else if (e.event === "error") setLive(false);
        else void qc.invalidateQueries({ queryKey: ["incoming"] });
      }),
    [qc],
  );

  const act = useMutation({
    mutationFn: async (v: { kind: "decide" | "arrived" | "ready"; id: string; action?: string; reason?: string }) => {
      if (v.kind === "decide") return api(`/hospital/referrals/${v.id}`, { method: "PATCH", body: { action: v.action, reason: v.reason } });
      if (v.kind === "arrived") return api(`/hospital/referrals/${v.id}/arrived`, { method: "POST" });
      return api(`/hospital/alerts/${v.id}/ready`, { method: "POST" });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["incoming"] }),
    // Arrival opens the encounter: go straight to it.
    onSuccess: (data, v) => {
      const enc = (data as { encounter_id?: string | null } | undefined)?.encounter_id;
      if (v.kind === "arrived" && enc) router.push(`/hospital/patients/${enc}`);
    },
  });

  const open = items.filter((i) => ["pending", "more_info", "sent", "ready", "accepted", "overdue"].includes(i.status));
  const done = items.filter((i) => !open.includes(i));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Incoming</h1>
        <AlertsButton who="staff" className="ml-auto mr-3" />
        <span className={cn("inline-flex items-center gap-1.5 text-sm", live ? "text-primary" : "text-muted-foreground")}>
          <Radio className={cn("h-4 w-4", live && "vt-pulse")} aria-hidden /> {live ? "Live" : "Connecting…"}
        </span>
      </div>
      {act.error ? <p className="rounded-lg bg-emergency-soft p-2 text-sm text-emergency">{(act.error as Error).message}</p> : null}
      {isLoading ? <p className="text-muted-foreground">Loading…</p> : null}
      {!isLoading && !open.length ? (
        <Card className="text-center text-muted-foreground">No incoming patients right now.</Card>
      ) : null}
      <div className="grid gap-3 lg:grid-cols-2">
        {open.map((i) => (
          <IncomingCard
            key={i.id}
            item={i}
            role={me?.role ?? ""}
            careLabel={careLabels[i.care_type ?? ""] ?? i.care_type ?? "—"}
            isNew={fresh.has(i.id)}
            busy={act.isPending}
            onAct={(v) => act.mutate({ ...v, id: i.id })}
          />
        ))}
      </div>
      {done.length ? (
        <>
          <h2 className="pt-2 text-lg font-bold text-muted-foreground">Earlier today</h2>
          <div className="grid gap-2 lg:grid-cols-2">
            {done.map((i) => (
              <Card key={i.id} className={cn("py-3", fresh.has(i.id) && "vt-new")}>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono font-semibold">{i.patient.vitalis_id}</span>
                  <Badge tone={STATUS_TONE[i.status] ?? "neutral"}>{i.status.replace("_", " ")}</Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  {careLabels[i.care_type ?? ""] ?? i.care_type} · {timeAgo(i.created_at)}
                  {i.decision_reason ? ` · ${i.decision_reason}` : ""}
                </p>
              </Card>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}

function IncomingCard({
  item: i,
  role,
  careLabel,
  isNew,
  busy,
  onAct,
}: {
  item: IncomingItem;
  role: string;
  careLabel: string;
  isNew: boolean;
  busy: boolean;
  onAct: (v: { kind: "decide" | "arrived" | "ready"; action?: string; reason?: string }) => void;
}) {
  const [declining, setDeclining] = useState(false);
  const [other, setOther] = useState("");
  const canDecide = DECIDERS.includes(role);
  const canArrive = FRONT_DESK.includes(role);
  const p = i.patient;
  return (
    <Card className={cn("space-y-3", i.red_flag && "border-l-4 border-l-emergency", isNew && "vt-new")}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            {i.kind === "alert" ? <BellRing className="h-5 w-5 text-emergency" aria-hidden /> : <UserRound className="h-5 w-5" aria-hidden />}
            <span className="font-mono text-lg font-bold">{p.vitalis_id}</span>
          </div>
          <p className="text-sm text-muted-foreground">
            {AGE[p.age_group ?? ""] ?? "Age ?"} · {p.sex ?? "sex ?"}
            {p.pregnant ? " · pregnant" : ""}
            {i.referred_by ? ` · via ${i.referred_by}` : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Badge tone="info">{careLabel}</Badge>
          <Badge tone={STATUS_TONE[i.status] ?? "neutral"}>
            {i.kind === "alert" ? (i.status === "ready" ? "heads-up · you said ready" : "heads-up") : i.status.replace("_", " ")}
          </Badge>
        </div>
      </div>

      {i.red_flag_message ? (
        <p className="flex items-start gap-2 rounded-lg bg-emergency-soft p-2 text-sm font-semibold text-emergency">
          <Siren className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /> {i.red_flag_message}
        </p>
      ) : null}

      <div>
        <p className="text-xs font-semibold uppercase text-muted-foreground">Symptoms</p>
        <ul className="mt-1 flex flex-wrap gap-1.5">
          {i.symptoms.map((s) => (
            <li key={s.code} className="rounded-md bg-muted px-2 py-1 text-sm">
              {s.label}
              {s.severity ? ` · ${s.severity}/5` : ""}
              {s.onset ? ` · ${s.onset}` : ""}
            </li>
          ))}
        </ul>
      </div>

      {i.vitals.length ? (
        <div>
          <p className="text-xs font-semibold uppercase text-muted-foreground">Recent vitals</p>
          <ul className="mt-1 flex flex-wrap gap-1.5 text-sm">
            {i.vitals.slice(0, 6).map((v, idx) => (
              <li key={idx} className="rounded-md bg-muted px-2 py-1">
                {v.kind.replace("_", " ")} {v.value}
                {v.unit} <span className="text-muted-foreground">({v.source}, {timeAgo(v.measured_at)})</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <Clock className="h-4 w-4" aria-hidden /> received {clockTime(i.created_at)}
        </span>
        {i.eta_minutes != null ? (
          <span>
            {i.distance_km} km · ETA ~{i.eta_minutes} min (estimate)
          </span>
        ) : null}
        {i.expected_arrival_at ? <span>expected by {clockTime(i.expected_arrival_at)}</span> : null}
      </div>

      {/* Actions */}
      {i.kind === "alert" && i.status === "sent" && canDecide ? (
        <Button size="lg" className="w-full" disabled={busy} onClick={() => onAct({ kind: "ready" })}>
          <CheckCircle2 className="h-5 w-5" /> We are ready
        </Button>
      ) : null}

      {i.kind === "referral" && (i.status === "pending" || i.status === "more_info") && canDecide ? (
        declining ? (
          <div className="space-y-2 rounded-lg bg-muted p-2">
            <p className="text-sm font-semibold">Why can&apos;t you take this patient?</p>
            <div className="flex flex-wrap gap-2">
              {DECLINE_REASONS.map((r) => (
                <Button key={r} variant="outline" size="sm" disabled={busy} onClick={() => onAct({ kind: "decide", action: "decline", reason: r })}>
                  {r}
                </Button>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                value={other}
                onChange={(e) => setOther(e.target.value)}
                placeholder="Other reason"
                className="h-9 flex-1 rounded-lg border border-border bg-card px-2 text-sm"
              />
              <Button size="sm" variant="outline" disabled={!other.trim() || busy} onClick={() => onAct({ kind: "decide", action: "decline", reason: other })}>
                Decline
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setDeclining(false)}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-2">
            <Button size="lg" className="col-span-2" disabled={busy} onClick={() => onAct({ kind: "decide", action: "accept" })}>
              Accept
            </Button>
            <Button size="lg" variant="outline" disabled={busy} onClick={() => setDeclining(true)}>
              Decline
            </Button>
          </div>
        )
      ) : null}

      {i.kind === "referral" && (i.status === "accepted" || i.status === "overdue") && canArrive ? (
        <Button size="lg" variant="mint" className="w-full" disabled={busy} onClick={() => onAct({ kind: "arrived" })}>
          Confirm arrival &amp; open encounter
        </Button>
      ) : null}
      {!canDecide && i.kind === "referral" && i.status === "pending" ? (
        <p className="text-sm text-muted-foreground">Waiting for a doctor or nurse to accept.</p>
      ) : null}
    </Card>
  );
}
