"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, TriangleAlert } from "lucide-react";
import { DailyBars, HBars, Stat } from "@/components/admin/Charts";
import { Badge, Card } from "@/components/ui/card";
import { api, type Schemas } from "@/lib/api";
import { timeAgo } from "@/lib/utils";

const pct = (x: number | null | undefined) => (x == null ? "—" : `${Math.round(x * 1000) / 10}%`);
const ACTION: Record<string, string> = { accepted: "Accepted by the doctor", edited: "Edited", rejected: "Rejected", pending: "Not reviewed yet" };

export default function ModelsPage() {
  const { data: m } = useQuery({
    queryKey: ["admin-models"],
    queryFn: () => api<Schemas["Models"]>("/admin/console/models"),
    refetchInterval: 30000,
  });
  if (!m) return <p className="text-muted-foreground">Loading…</p>;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Models</h1>
        <p className="text-sm text-muted-foreground">
          The triage disease model, the team&apos;s diabetes and heart risk models, and the doctor&apos;s AI drafts. If the
          disease model is down, triage keeps working on the red-flag rules alone.
        </p>
      </div>

      <Card className="flex items-center gap-3">
        {m.service_up ? <CheckCircle2 className="h-6 w-6 text-primary" aria-hidden /> : <TriangleAlert className="h-6 w-6 text-emergency" aria-hidden />}
        <div>
          <p className="font-semibold">Disease model service: {m.service_up ? "up" : "not answering"}</p>
          <p className="text-sm text-muted-foreground">{m.service_up ? `Answered a health check in ${m.service_ms} ms.` : "Triage is running on the red-flag rules alone."}</p>
        </div>
      </Card>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Triage model calls" value={m.triage_calls} sub={`${m.triage_calls_24h} in the last 24 h`} />
        <Stat label="Answered successfully" value={pct(m.triage_ok_rate)} />
        <Stat label="Average time" value={m.triage_avg_ms == null ? "—" : `${Math.round(m.triage_avg_ms)} ms`} sub="last 14 days" />
        <Stat label="Slowest 5%" value={m.triage_p95_ms == null ? "—" : `${Math.round(m.triage_p95_ms)} ms`} sub="95th percentile" />
      </section>

      <DailyBars title="Triage model calls per day" rows={m.series.map((r) => ({ ...r, date: String(r.date) }))} series={[
        { key: "ok", label: "Answered", color: "var(--series-1)" },
        { key: "failed", label: "Failed or timed out", color: "var(--series-2)" },
      ]} height={140} />

      {m.triage_last_error ? (
        <Card className="text-sm">
          <p className="font-semibold">Last failure {m.triage_last_error_at ? timeAgo(m.triage_last_error_at) : ""}</p>
          <p className="mt-1 font-mono text-xs text-muted-foreground">{m.triage_last_error}</p>
        </Card>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="space-y-2">
          <h2 className="font-semibold">Model versions</h2>
          <ul className="space-y-1 text-sm">
            {m.triage_versions.map((v) => (
              <li key={v.version} className="flex justify-between gap-2">
                <span className="font-mono text-xs">{v.version}</span>
                <span className="tabular-nums text-muted-foreground">{v.calls} calls · {pct(v.ok_rate)} ok</span>
              </li>
            ))}
            {!m.triage_versions.length ? <li className="text-muted-foreground">No calls yet.</li> : null}
          </ul>
          <p className="pt-2 text-sm">
            Diabetes and heart risk models: <Badge tone={m.risk_models_enabled ? "ok" : "neutral"}>{m.risk_models_enabled ? "on" : "off"}</Badge>
          </p>
          {m.ai_model_versions.length ? (
            <p className="text-xs text-muted-foreground">Seen in AI drafts: {m.ai_model_versions.join(", ")}</p>
          ) : null}
        </Card>
        <HBars title={`Doctor's AI drafts (${m.ai_drafts})`}
          items={Object.entries(m.ai_by_action).map(([k, v]) => ({ label: ACTION[k] ?? k, value: v }))}
          note={Object.entries(m.ai_by_provider).map(([k, v]) => `${k}: ${v}`).join(" · ") || undefined} />
      </div>
    </div>
  );
}
