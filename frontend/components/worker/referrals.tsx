"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Siren } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge, Card } from "@/components/ui/card";
import { api, type Schemas } from "@/lib/api";
import { subscribe } from "@/lib/sse";
import { clockTime, cn, timeAgo } from "@/lib/utils";

export type WorkerReferral = Schemas["WorkerReferralOut"];

export const STATUS: Record<string, { label: string; tone: "ok" | "warn" | "danger" | "neutral" | "info" }> = {
  pending: { label: "Waiting for hospital", tone: "warn" },
  more_info: { label: "Hospital needs info", tone: "warn" },
  accepted: { label: "Accepted — on the way", tone: "ok" },
  declined: { label: "Declined", tone: "neutral" },
  cancelled: { label: "Cancelled", tone: "neutral" },
  arrived: { label: "Arrived", tone: "info" },
  completed: { label: "Completed", tone: "neutral" },
  overdue: { label: "Overdue — check on them", tone: "danger" },
};

/** Live list of this worker's referrals (SSE on worker:<id>, polling as a safety net). */
export function useWorkerReferrals() {
  const qc = useQueryClient();
  const [live, setLive] = useState(false);
  const q = useQuery({
    queryKey: ["worker-referrals"],
    queryFn: () => api<WorkerReferral[]>("/worker/referrals"),
    refetchInterval: 20000,
  });
  useEffect(
    () =>
      subscribe("/worker/referrals/stream", (e) => {
        if (e.event === "ready") setLive(true);
        else if (e.event === "error") setLive(false);
        else {
          void qc.invalidateQueries({ queryKey: ["worker-referrals"] });
          void qc.invalidateQueries({ queryKey: ["worker-referral"] });
        }
      }),
    [qc],
  );
  return { ...q, live };
}

export function RecentReferrals({ limit }: { limit?: number }) {
  const { data = [], isLoading } = useWorkerReferrals();
  // Hide declined hops that were automatically passed on: the next referral carries the story.
  const rows = data.filter((r) => !(r.status === "declined" && r.next_referral_id)).slice(0, limit ?? 100);
  if (isLoading) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (!rows.length) return <Card className="text-sm text-muted-foreground">No referrals in the last 7 days.</Card>;
  return (
    <div className="grid gap-2">
      {rows.map((r) => (
        <Link key={r.id} href={`/worker/referrals/${r.id}`}>
          <Card className={cn("py-3 hover:bg-muted", r.status === "overdue" && "border-2 border-emergency")}>
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono font-semibold">{r.vitalis_id}</span>
              <Badge tone={STATUS[r.status]?.tone ?? "neutral"}>{STATUS[r.status]?.label ?? r.status}</Badge>
            </div>
            <div className="mt-1 flex items-center gap-1.5 text-sm">
              {r.red_flag ? <Siren className="h-4 w-4 text-emergency" aria-label="Danger sign" /> : null}
              <span className="truncate">{r.facility_name}</span>
            </div>
            <div className="text-xs text-muted-foreground">
              {r.care_label ?? r.care_type} · sent {timeAgo(r.created_at)}
              {r.accepted_at ? ` · accepted ${clockTime(r.accepted_at)}` : ""}
              {r.arrived_at ? ` · arrived ${clockTime(r.arrived_at)}` : ""}
            </div>
          </Card>
        </Link>
      ))}
    </div>
  );
}
