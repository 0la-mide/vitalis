"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Radio, Siren } from "lucide-react";
import { useState } from "react";
import { useFacilityStream } from "@/components/hospital/useFacilityStream";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/card";
import { inputCls } from "@/components/ui/field";
import { api, type Schemas } from "@/lib/api";
import { useMe } from "@/lib/staff";
import { clockTime, cn } from "@/lib/utils";

type Item = Schemas["LabQueueItem"];

export default function LabQueue() {
  const { data: me } = useMe();
  const qc = useQueryClient();
  const isLab = me?.role === "lab";
  const { data: items = [], isLoading } = useQuery({
    queryKey: ["lab-queue"],
    queryFn: () => api<Item[]>("/hospital/lab/queue"),
    enabled: isLab,
    refetchInterval: 30000,
  });
  const live = useFacilityStream([["lab-queue"]]);
  const { data: tests = [] } = useQuery({
    queryKey: ["tests"],
    queryFn: () => api<Schemas["TestOption"][]>("/hospital/tests"),
    staleTime: Infinity,
    enabled: isLab,
  });
  const params = (code: string) => tests.find((t) => t.code === code)?.params ?? [];
  const act = useMutation({
    mutationFn: ({ id, path, body }: { id: string; path: string; body?: unknown }) =>
      api(`/hospital/orders/${id}/${path}`, { body: body ?? {} }),
    onSettled: () => qc.invalidateQueries({ queryKey: ["lab-queue"] }),
  });

  if (!isLab) return <Card>The lab queue is for lab and radiology staff.</Card>;
  const toResult = items.filter((i) => i.order.status === "ordered");
  const toVerify = items.filter((i) => i.order.status === "resulted");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Lab &amp; radiology</h1>
        <span className={cn("inline-flex items-center gap-1.5 text-sm", live ? "text-primary" : "text-muted-foreground")}>
          <Radio className={cn("h-4 w-4", live && "vt-pulse")} /> {live ? "Live" : "Connecting…"}
        </span>
      </div>
      {act.error ? <p className="rounded-lg bg-emergency-soft p-2 text-sm text-emergency">{(act.error as Error).message}</p> : null}
      {isLoading ? <p className="text-muted-foreground">Loading…</p> : null}
      <section className="space-y-2">
        <h2 className="font-bold">To result ({toResult.length})</h2>
        {!toResult.length ? <Card className="text-sm text-muted-foreground">Nothing waiting.</Card> : null}
        {toResult.map((i) => <ResultForm key={i.order.id} i={i} params={params(i.order.test_code)} busy={act.isPending}
          onSave={(text, abnormal, values) => act.mutate({ id: i.order.id, path: "result", body: { result_text: text, abnormal, values } })} />)}
      </section>
      <section className="space-y-2">
        <h2 className="font-bold">To verify ({toVerify.length})</h2>
        <p className="text-sm text-muted-foreground">Check each result against the request, then verify. Only verified results go back to the doctor.</p>
        {toVerify.map((i) => (
          <Card key={i.order.id} className="space-y-2">
            <Header i={i} />
            <p className={cn("whitespace-pre-wrap rounded-lg bg-muted p-2 text-sm", i.order.abnormal && "font-semibold text-emergency")}>
              {i.order.abnormal ? "ABNORMAL: " : ""}{i.order.result_text}
            </p>
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-muted-foreground">entered by {i.order.entered_by} {clockTime(i.order.entered_at)}</span>
              <Button size="sm" disabled={act.isPending} onClick={() => act.mutate({ id: i.order.id, path: "verify" })}>
                <CheckCircle2 className="h-4 w-4" /> Verify
              </Button>
            </div>
          </Card>
        ))}
      </section>
    </div>
  );
}

function Header({ i }: { i: Item }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div>
        <span className="font-semibold">{i.order.test_name}</span>{" "}
        <span className="text-sm text-muted-foreground">· {i.order.category} · <span className="font-mono">{i.vitalis_id}</span></span>
      </div>
      <div className="flex gap-1.5">
        {i.emergency ? <Badge tone="danger"><Siren className="h-3 w-3" /> emergency</Badge> : null}
        {i.order.priority === "urgent" ? <Badge tone="danger">urgent</Badge> : <Badge>routine</Badge>}
      </div>
    </div>
  );
}

type Param = Schemas["TestParam"];

function ResultForm({ i, params, busy, onSave }: {
  i: Item; params: Param[]; busy: boolean;
  onSave: (t: string, abnormal: boolean, values: Record<string, { value: number | string; unit?: string }> | null) => void;
}) {
  const [text, setText] = useState("");
  const [abnormal, setAbnormal] = useState(false);
  const [vals, setVals] = useState<Record<string, string>>({});
  const filled = params.filter((p) => (vals[p.name] ?? "").trim() !== "");
  const save = () => {
    const values = filled.length
      ? Object.fromEntries(filled.map((p) => {
          const raw = vals[p.name].trim();
          const num = Number(raw);
          return [p.name, { value: p.choices || Number.isNaN(num) ? raw : num, unit: p.unit || undefined }];
        }))
      : null;
    onSave(text, abnormal, values);
  };
  return (
    <Card className="space-y-2">
      <Header i={i} />
      <p className="text-xs text-muted-foreground">ordered by {i.order.ordered_by} at {clockTime(i.order.created_at)}{i.order.clinical_note ? ` — ${i.order.clinical_note}` : ""}</p>
      {params.length ? (
        <div className="grid gap-2 sm:grid-cols-2">
          {params.map((p) => (
            <label key={p.name} className="grid gap-0.5 text-xs font-medium">
              <span>{p.name}{p.unit ? <span className="font-normal text-muted-foreground"> ({p.unit})</span> : null}
                {p.lo != null || p.hi != null ? <span className="font-normal text-muted-foreground"> · ref {p.lo ?? "–"}–{p.hi ?? "–"}</span> : null}</span>
              {p.choices ? (
                <select value={vals[p.name] ?? ""} onChange={(e) => setVals({ ...vals, [p.name]: e.target.value })} className={cn(inputCls, "h-10")}>
                  <option value="">—</option>{p.choices.map((c) => <option key={c}>{c}</option>)}
                </select>
              ) : (
                <input type="number" step="any" inputMode="decimal" value={vals[p.name] ?? ""}
                  onChange={(e) => setVals({ ...vals, [p.name]: e.target.value })} className={cn(inputCls, "h-10")} />
              )}
            </label>
          ))}
        </div>
      ) : null}
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={2}
        placeholder={i.order.category === "radiology" ? "Report" : params.length ? "Comment (optional)" : "Result"} className={cn(inputCls, "h-auto py-2")} />
      <div className="flex items-center justify-between gap-2">
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={abnormal} onChange={(e) => setAbnormal(e.target.checked)} /> Abnormal</label>
        <Button size="sm" disabled={busy || (!text.trim() && !filled.length)} onClick={save}>Save result</Button>
      </div>
    </Card>
  );
}
