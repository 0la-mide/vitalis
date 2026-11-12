"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, Card } from "@/components/ui/card";
import { api, type Schemas } from "@/lib/api";
import { cn, timeAgo } from "@/lib/utils";

type Row = Schemas["ServiceRow"];
const OPTIONS = [
  { v: "available", label: "Available", cls: "bg-primary text-primary-foreground" },
  { v: "limited", label: "Limited", cls: "bg-warning-soft text-warning" },
  { v: "unavailable", label: "Not available", cls: "bg-emergency-soft text-emergency" },
] as const;

export default function AvailabilityPage() {
  const qc = useQueryClient();
  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["services"],
    queryFn: () => api<Row[]>("/hospital/services"),
  });
  const update = useMutation({
    mutationFn: (v: { id: string; status: string }) =>
      api<Row[]>(`/hospital/services/${v.id}`, { method: "PATCH", body: { availability_status: v.status } }),
    onSuccess: (data) => qc.setQueryData(["services"], data),
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Availability</h1>
        <p className="text-sm text-muted-foreground">
          One tap per service. Every tap stamps the time, so patients and referrers see how fresh it is. Confirmed means
          updated in the last 6 hours.
        </p>
      </div>
      {isLoading ? <p className="text-muted-foreground">Loading…</p> : null}
      <div className="grid gap-2 md:grid-cols-2">
        {rows.map((r) => (
          <Card key={r.id} className="py-3">
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold">{r.name}</span>
              <Badge tone={r.freshness === "confirmed" ? "ok" : r.freshness === "stale" ? "warn" : "neutral"}>
                {r.freshness} · {timeAgo(r.last_confirmed_at)}
              </Badge>
            </div>
            <div className="mt-2 grid grid-cols-3 gap-1.5">
              {OPTIONS.map((o) => (
                <button
                  key={o.v}
                  type="button"
                  disabled={update.isPending}
                  onClick={() => update.mutate({ id: r.id, status: o.v })}
                  aria-pressed={r.availability_status === o.v}
                  className={cn(
                    "min-h-11 rounded-lg border-2 text-sm font-semibold",
                    r.availability_status === o.v ? cn(o.cls, "border-transparent") : "border-border bg-card",
                  )}
                >
                  {o.label}
                </button>
              ))}
            </div>
            {r.availability_status === "unknown" ? (
              <p className="mt-1 text-xs text-muted-foreground">Currently unknown — tap to confirm.</p>
            ) : null}
          </Card>
        ))}
      </div>
    </div>
  );
}
