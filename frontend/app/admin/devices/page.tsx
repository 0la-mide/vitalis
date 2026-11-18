"use client";

import { useQuery } from "@tanstack/react-query";
import { HBars, Stat } from "@/components/admin/Charts";
import { Card } from "@/components/ui/card";
import { api, type Schemas } from "@/lib/api";
import { timeAgo } from "@/lib/utils";

const bars = (o: Record<string, number>) =>
  Object.entries(o).map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value);

export default function DevicesPage() {
  const { data: d } = useQuery({
    queryKey: ["admin-devices"],
    queryFn: () => api<Schemas["Devices"]>("/admin/console/devices"),
    refetchInterval: 30000,
  });
  if (!d) return <p className="text-muted-foreground">Loading…</p>;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Devices</h1>
        <p className="text-sm text-muted-foreground">
          Each patient&apos;s phone holds one VITALIS card. Patient phones are anonymous here: no names, no VITALIS IDs.
        </p>
      </div>
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Phones with a VITALIS card" value={d.phones_with_card} />
        <Stat label="Active today" value={d.phones_active_24h} sub="used VITALIS in the last 24 h" />
        <Stat label="Active this week" value={d.phones_active_7d} sub={`${d.phones_active_30d} in the last 30 days`} />
        <Stat label="Devices getting alerts" value={d.alerts_total} sub={`${d.alerts_patients} patients · ${d.alerts_staff} staff`} />
      </section>
      <div className="grid gap-4 lg:grid-cols-2">
        <HBars title="Alerts by browser" items={bars(d.by_browser)} />
        <HBars title="Alerts by phone or computer" items={bars(d.by_os)}
          note="From devices that turned on alerts. Devices registered before this update show as Unknown." />
      </div>
      <Card className="overflow-x-auto p-0">
        <h2 className="px-3 pt-3 font-semibold">Latest devices with alerts on</h2>
        <table className="mt-2 w-full text-sm">
          <thead className="bg-muted text-left text-xs uppercase text-muted-foreground">
            <tr><th className="px-3 py-2">Whose</th><th className="px-3 py-2">Browser</th><th className="px-3 py-2">Device</th><th className="px-3 py-2">Since</th></tr>
          </thead>
          <tbody>
            {d.recent.map((r, i) => (
              <tr key={i} className="border-t border-border">
                <td className="px-3 py-2 capitalize">{r.owner}</td>
                <td className="px-3 py-2">{r.browser}</td>
                <td className="px-3 py-2">{r.os}</td>
                <td className="px-3 py-2">{timeAgo(r.since)}</td>
              </tr>
            ))}
            {!d.recent.length ? <tr><td colSpan={4} className="px-3 py-6 text-center text-muted-foreground">No device has turned on alerts yet.</td></tr> : null}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
