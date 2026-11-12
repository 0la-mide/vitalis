"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Card } from "@/components/ui/card";
import { api, type Schemas } from "@/lib/api";

function Stat({ label, value, sub, href }: { label: string; value: string | number; sub?: string; href?: string }) {
  const body = (
    <Card className="h-full">
      <div className="text-sm text-muted-foreground">{label}</div>
      <div className="mt-1 text-3xl font-bold tabular-nums">{value}</div>
      {sub ? <div className="mt-1 text-xs text-muted-foreground">{sub}</div> : null}
    </Card>
  );
  return href ? <Link href={href} className="block hover:opacity-90">{body}</Link> : body;
}

function duration(s: number | null | undefined) {
  if (s == null) return "—";
  if (s < 90) return `${Math.round(s)} s`;
  return `${Math.round(s / 60)} min`;
}

export default function AdminOverview() {
  const { data: m } = useQuery({
    queryKey: ["admin-metrics"],
    queryFn: () => api<Schemas["Metrics"]>("/admin/metrics"),
    refetchInterval: 15000,
  });
  if (!m) return <p className="text-muted-foreground">Loading…</p>;
  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-bold">Network</h1>
        <p className="text-sm text-muted-foreground">Counts only — no patient names or identifiers.</p>
      </section>
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Pending facilities" value={m.facilities_pending} sub={`${m.facilities_approved} approved`}
          href="/admin/verifications?kind=facility" />
        <Stat label="Pending workers" value={m.workers_pending} sub={`${m.workers_approved} approved`}
          href="/admin/verifications?kind=worker" />
        <Stat label="Triage reports" value={m.triage_reports} sub={`${m.red_flags} with a red flag`} />
        <Stat label="Referrals" value={m.referrals} sub={`${m.referrals_accepted} accepted · ${m.referrals_declined} declined`} />
        <Stat label="Median time to acceptance" value={duration(m.median_acceptance_seconds)} />
        <Stat label="Arrival rate" value={m.arrival_rate == null ? "—" : `${Math.round(m.arrival_rate * 100)}%`}
          sub="arrived ÷ accepted" />
        <Stat label="Overdue now" value={m.overdue_now} />
      </section>
    </div>
  );
}
