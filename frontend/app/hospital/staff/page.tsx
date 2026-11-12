"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/card";
import { inputCls } from "@/components/ui/field";
import { api, type Schemas } from "@/lib/api";
import { ROLE_LABEL, useMe } from "@/lib/staff";
import { cn, timeAgo } from "@/lib/utils";

type Row = Schemas["StaffRow"];
const TONE: Record<string, "ok" | "warn" | "danger" | "neutral"> = {
  pending: "warn", approved: "ok", rejected: "danger", suspended: "danger",
};

export default function StaffPage() {
  const { data: me } = useMe();
  const qc = useQueryClient();
  const isAdmin = me?.role === "facility_admin";
  const { data: rows = [], isLoading, error } = useQuery({
    queryKey: ["staff"],
    queryFn: () => api<Row[]>("/hospital/staff"),
    enabled: isAdmin,
  });
  const decide = useMutation({
    mutationFn: (v: { id: string; decision: string; reason?: string }) =>
      api<Row[]>(`/hospital/staff/${v.id}`, { method: "PATCH", body: { decision: v.decision, reason: v.reason } }),
    onSuccess: (data) => qc.setQueryData(["staff"], data),
  });

  if (!isAdmin) return <Card>Only the facility admin can manage staff.</Card>;
  const pending = rows.filter((r) => r.status === "pending");
  const others = rows.filter((r) => r.status !== "pending");

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Staff</h1>
        <p className="text-sm text-muted-foreground">
          Check each professional licence number before approving. Staff see patient data only after approval.
        </p>
      </div>
      {isLoading ? <p className="text-muted-foreground">Loading…</p> : null}
      {error ? <p className="text-emergency">{(error as Error).message}</p> : null}
      {decide.error ? <p className="rounded-lg bg-emergency-soft p-2 text-sm text-emergency">{(decide.error as Error).message}</p> : null}

      <h2 className="text-lg font-bold">Waiting for approval ({pending.length})</h2>
      {!pending.length && !isLoading ? <Card className="text-muted-foreground">No one is waiting.</Card> : null}
      <div className="grid gap-2 md:grid-cols-2">
        {pending.map((r) => <StaffCard key={r.user_id} r={r} busy={decide.isPending}
          onDecide={(decision, reason) => decide.mutate({ id: r.user_id, decision, reason })} />)}
      </div>

      <h2 className="pt-2 text-lg font-bold">Team ({others.length})</h2>
      <div className="grid gap-2 md:grid-cols-2">
        {others.map((r) => <StaffCard key={r.user_id} r={r} busy={decide.isPending}
          onDecide={(decision, reason) => decide.mutate({ id: r.user_id, decision, reason })} />)}
      </div>
    </div>
  );
}

function StaffCard({ r, busy, onDecide }: { r: Row; busy: boolean; onDecide: (d: string, reason?: string) => void }) {
  const [mode, setMode] = useState<null | "reject" | "suspend">(null);
  const [reason, setReason] = useState("");
  return (
    <Card className="space-y-2 py-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-semibold">{r.full_name}</div>
          <div className="text-sm text-muted-foreground">{ROLE_LABEL[r.role] ?? r.role} · {r.email}</div>
          <div className="text-sm">Licence: <span className="font-mono">{r.licence_number ?? "—"}</span></div>
        </div>
        <div className="text-right">
          <Badge tone={TONE[r.status] ?? "neutral"}>{r.status}</Badge>
          <div className="mt-1 text-xs text-muted-foreground">joined {timeAgo(r.created_at)}</div>
        </div>
      </div>
      {r.status_reason ? <p className="text-sm text-muted-foreground">Reason: {r.status_reason}</p> : null}
      {mode ? (
        <div className="flex flex-wrap gap-2">
          <input autoFocus value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason"
            className={cn(inputCls, "h-9 flex-1")} />
          <Button size="sm" variant="outline" disabled={!reason.trim() || busy} onClick={() => onDecide(mode, reason)}>
            Confirm {mode}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setMode(null)}>Cancel</Button>
        </div>
      ) : (
        <div className="flex gap-2">
          {r.status === "pending" ? (
            <>
              <Button size="sm" disabled={busy} onClick={() => onDecide("approve")}>Approve</Button>
              <Button size="sm" variant="outline" onClick={() => setMode("reject")}>Reject</Button>
            </>
          ) : null}
          {r.status === "approved" ? <Button size="sm" variant="outline" onClick={() => setMode("suspend")}>Suspend</Button> : null}
          {r.status === "suspended" ? <Button size="sm" variant="outline" disabled={busy} onClick={() => onDecide("approve")}>Reinstate</Button> : null}
        </div>
      )}
    </Card>
  );
}
