"use client";

import { useQuery } from "@tanstack/react-query";
import { Award } from "lucide-react";
import { Card } from "@/components/ui/card";
import { api, type Schemas } from "@/lib/api";

/** The chemist's month: the difference they made, in three numbers and a badge or two. */
export function MonthCard() {
  const { data } = useQuery({ queryKey: ["worker-stats"], queryFn: () => api<Schemas["WorkerStats"]>("/worker/stats") });
  if (!data) return null;
  const stats = [
    [data.patients_referred, "patients referred"],
    [data.reached_hospital, "reached a hospital"],
    [data.emergencies, "emergencies"],
  ] as const;
  return (
    <Card className="space-y-3">
      <p className="text-sm font-semibold text-muted-foreground">Your {data.month}</p>
      <div className="grid grid-cols-3 gap-2 text-center">
        {stats.map(([n, l]) => (
          <div key={l} className="rounded-lg bg-mint p-2">
            <div className="text-3xl font-bold text-primary">{n}</div>
            <div className="text-xs font-medium">{l}</div>
          </div>
        ))}
      </div>
      {data.badges.length ? (
        <ul className="space-y-1">
          {data.badges.map((b) => (
            <li key={b} className="flex items-center gap-2 text-sm font-semibold"><Award className="h-4 w-4 text-primary" /> {b}</li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">Every patient you send to the right hospital counts here.</p>
      )}
    </Card>
  );
}
