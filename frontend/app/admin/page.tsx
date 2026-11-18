"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { DailyBars, HBars, ROLE_LABEL, Stat } from "@/components/admin/Charts";
import { Card } from "@/components/ui/card";
import { api, type Schemas } from "@/lib/api";
import { cn } from "@/lib/utils";

function duration(s: number | null | undefined) {
  if (s == null) return "—";
  if (s < 90) return `${Math.round(s)} s`;
  return `${Math.round(s / 60)} min`;
}

const CHANNELS = [
  { key: "app", label: "Family app", color: "var(--series-1)" },
  { key: "chemist", label: "Chemist", color: "var(--series-2)" },
  { key: "ussd", label: "USSD (any phone)", color: "var(--series-3)" },
];

export default function AdminOverview() {
  const [days, setDays] = useState(30);
  const { data: m } = useQuery({
    queryKey: ["admin-metrics"],
    queryFn: () => api<Schemas["Metrics"]>("/admin/metrics"),
    refetchInterval: 15000,
  });
  const { data: o } = useQuery({
    queryKey: ["admin-overview", days],
    queryFn: () => api<Schemas["Overview"]>(`/admin/console/overview?days=${days}`),
    refetchInterval: 30000,
  });
  if (!m || !o) return <p className="text-muted-foreground">Loading…</p>;
  const staff = Object.entries(o.accounts_by_role).reduce((a, [, n]) => a + n, 0);
  const rows = o.series.map((r) => ({ ...r, date: String(r.date) }));

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Network</h1>
          <p className="text-sm text-muted-foreground">Everything at a glance. Patients are counted, never named.</p>
        </div>
        <div className="flex gap-1 rounded-lg bg-muted p-1 text-sm font-semibold" role="group" aria-label="Period">
          {[7, 30, 90].map((d) => (
            <button key={d} type="button" onClick={() => setDays(d)}
              className={cn("rounded-md px-3 py-1.5", days === d ? "bg-card shadow-sm" : "text-muted-foreground")}>
              {d} days
            </button>
          ))}
        </div>
      </section>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Patients (phones with a card)" value={o.patients} sub={`${o.patients_active_24h} active today · ${o.patients_active_7d} this week`} />
        <Stat label="Staff and chemist accounts" value={staff} sub={`${o.accounts_by_status.pending ?? 0} waiting for approval`} />
        <Stat label="Requests for care" value={o.funnel.requests} sub={`${m.red_flags} emergencies`} />
        <Stat label="Sign-ins today" value={o.sign_ins_24h} sub={`${o.devices_with_alerts} devices get alerts`} />
      </section>

      <DailyBars title="Requests for care, by how they came in" rows={rows} series={CHANNELS} />

      <div className="grid gap-4 lg:grid-cols-2">
        <DailyBars title="New sign-ups" rows={rows} series={[
          { key: "new_patients", label: "Patients", color: "var(--series-1)" },
          { key: "new_accounts", label: "Staff and chemists", color: "var(--series-2)" },
        ]} height={140} />
        <DailyBars title="Staff sign-ins" rows={rows} series={[{ key: "sign_ins", label: "Sign-ins", color: "var(--series-1)" }]} height={140} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <HBars title="From request to bed" items={[
          { label: "Requests", value: o.funnel.requests },
          { label: "Sent to a hospital", value: o.funnel.referred },
          { label: "Accepted", value: o.funnel.accepted },
          { label: "Arrived", value: o.funnel.arrived },
        ]} note={`${o.funnel.declined} declined (and moved on to the next hospital). Median time to acceptance: ${duration(m.median_acceptance_seconds)}.`} />
        <HBars title="Accounts by role" items={Object.entries(o.accounts_by_role)
          .map(([k, v]) => ({ label: ROLE_LABEL[k] ?? k, value: v })).sort((a, b) => b.value - a.value)} />
      </div>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Patients started by a chemist" value={o.patients_by_chemist} />
        <Stat label="Patients reached by USSD" value={o.patients_by_ussd} />
        <Stat label="Arrival rate" value={m.arrival_rate == null ? "—" : `${Math.round(m.arrival_rate * 100)}%`} sub="arrived ÷ accepted" />
        <Stat label="Overdue now" value={m.overdue_now} />
      </section>

      <Card className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
        <Link href="/admin/verifications?kind=facility" className="underline underline-offset-2">
          Hospitals: {m.facilities_approved} approved · {m.facilities_pending} pending
        </Link>
        <Link href="/admin/verifications?kind=worker" className="underline underline-offset-2">
          Chemists: {m.workers_approved} approved · {m.workers_pending} pending
        </Link>
        <Link href="/admin/accounts" className="underline underline-offset-2">All accounts</Link>
        <Link href="/admin/devices" className="underline underline-offset-2">Devices</Link>
        <Link href="/admin/models" className="underline underline-offset-2">Models</Link>
      </Card>
    </div>
  );
}
