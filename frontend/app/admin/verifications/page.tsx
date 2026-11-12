"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, FileText, Pill } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/card";
import { inputCls } from "@/components/ui/field";
import { api, apiPage, type Schemas } from "@/lib/api";
import { cn, timeAgo } from "@/lib/utils";

type V = Schemas["VerificationOut"];
const STATUSES = ["pending", "approved", "rejected", "suspended", "all"] as const;
const KINDS = ["all", "facility", "worker"] as const;
const TONE: Record<string, "ok" | "warn" | "danger" | "neutral"> = {
  pending: "warn", approved: "ok", rejected: "danger", suspended: "danger",
};

export default function VerificationsPage() {
  return (
    <Suspense fallback={<p className="text-muted-foreground">Loading…</p>}>
      <Queue />
    </Suspense>
  );
}

function Queue() {
  const params = useSearchParams();
  const router = useRouter();
  const status = (params.get("status") ?? "pending") as (typeof STATUSES)[number];
  const kind = (params.get("kind") ?? "all") as (typeof KINDS)[number];
  const setParam = (k: string, v: string) => {
    const p = new URLSearchParams(params.toString());
    p.set(k, v);
    router.replace(`/admin/verifications?${p.toString()}`);
  };
  const { data, isLoading } = useQuery({
    queryKey: ["verifications", status, kind],
    queryFn: () => apiPage<V[]>(`/admin/verifications?status=${status}&kind=${kind}&limit=100`),
  });
  const items = data?.data ?? [];

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Verifications</h1>
      <p className="text-sm text-muted-foreground">
        Facilities and frontline workers. Hospital staff are approved by their own facility admin.
      </p>
      <div className="flex flex-wrap gap-2">
        <div className="flex rounded-lg bg-card p-1">
          {STATUSES.map((s) => (
            <button key={s} type="button" onClick={() => setParam("status", s)}
              className={cn("rounded-md px-3 py-1.5 text-sm font-semibold capitalize", status === s && "bg-mint")}>
              {s}
            </button>
          ))}
        </div>
        <div className="flex rounded-lg bg-card p-1">
          {KINDS.map((k) => (
            <button key={k} type="button" onClick={() => setParam("kind", k)}
              className={cn("rounded-md px-3 py-1.5 text-sm font-semibold capitalize", kind === k && "bg-mint")}>
              {k === "all" ? "All" : k === "facility" ? "Facilities" : "Workers"}
            </button>
          ))}
        </div>
      </div>
      {isLoading ? <p className="text-muted-foreground">Loading…</p> : null}
      {!isLoading && !items.length ? <Card className="text-center text-muted-foreground">Nothing here.</Card> : null}
      <div className="grid gap-3">
        {items.map((v) => <VerificationCard key={v.id} v={v} />)}
      </div>
      {data?.meta && data.meta.total > items.length ? (
        <p className="text-sm text-muted-foreground">Showing {items.length} of {data.meta.total}.</p>
      ) : null}
    </div>
  );
}

function VerificationCard({ v }: { v: V }) {
  const qc = useQueryClient();
  const [mode, setMode] = useState<null | "reject" | "suspend">(null);
  const [reason, setReason] = useState("");
  const decide = useMutation({
    mutationFn: (body: { decision: string; reason?: string }) =>
      api<V>(`/admin/verifications/${v.id}`, { method: "PATCH", body }),
    onSuccess: () => {
      setMode(null);
      setReason("");
      void qc.invalidateQueries({ queryKey: ["verifications"] });
      void qc.invalidateQueries({ queryKey: ["admin-metrics"] });
    },
  });
  const details = v.details as Record<string, unknown>;
  const isFacility = v.subject_type === "facility";

  return (
    <Card className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 rounded-lg bg-mint p-2 text-primary-strong">
            {isFacility ? <Building2 className="h-5 w-5" /> : <Pill className="h-5 w-5" />}
          </span>
          <div>
            <h2 className="text-lg font-bold leading-tight">{isFacility ? v.facility_name : v.user_name}</h2>
            <p className="text-sm text-muted-foreground">
              {isFacility
                ? `${v.facility_type} · ${v.facility_lga} · admin: ${v.user_name} (${v.user_email})`
                : `${String(details.worker_type ?? "worker")} · ${String(details.lga ?? "")} · ${v.user_email}`}
            </p>
          </div>
        </div>
        <div className="text-right">
          <Badge tone={TONE[v.status] ?? "neutral"}>{v.status}</Badge>
          <div className="mt-1 text-xs text-muted-foreground">submitted {timeAgo(v.created_at)}</div>
        </div>
      </div>

      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-muted-foreground">Licence number</dt>
        <dd className="font-mono">{String(details.licence_number ?? "—")}</dd>
        {details.business_name ? (<><dt className="text-muted-foreground">Business</dt><dd>{String(details.business_name)}</dd></>) : null}
        {Array.isArray(details.services) && details.services.length ? (
          <><dt className="text-muted-foreground">Services</dt><dd>{(details.services as string[]).join(", ").replace(/_/g, " ")}</dd></>
        ) : null}
        {details.resubmission_of ? (<><dt className="text-muted-foreground">Note</dt><dd>Resubmitted after a rejection</dd></>) : null}
        {v.reason ? (<><dt className="text-muted-foreground">Reason</dt><dd>{v.reason}</dd></>) : null}
        {v.reviewer_name ? (<><dt className="text-muted-foreground">Reviewed by</dt><dd>{v.reviewer_name} · {timeAgo(v.decided_at)}</dd></>) : null}
      </dl>

      <div className="flex flex-wrap gap-2">
        {v.documents.length ? v.documents.map((d) => (
          <a key={d.id} href={`/api/v1/admin/documents/${d.id}`} target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-sm font-semibold hover:bg-muted">
            <FileText className="h-4 w-4" /> {d.original_name} <span className="font-normal text-muted-foreground">({Math.ceil(d.size_bytes / 1024)} KB)</span>
          </a>
        )) : <span className="text-sm text-muted-foreground">No documents</span>}
      </div>

      {mode ? (
        <div className="flex flex-wrap gap-2 rounded-lg bg-muted p-2">
          <input autoFocus value={reason} onChange={(e) => setReason(e.target.value)}
            placeholder={mode === "reject" ? "Reason (shown to the applicant)" : "Reason for suspension"}
            className={cn(inputCls, "h-10 flex-1 min-w-48")} />
          <Button variant="outline" disabled={!reason.trim() || decide.isPending}
            onClick={() => decide.mutate({ decision: mode, reason })}>
            Confirm {mode}
          </Button>
          <Button variant="ghost" onClick={() => setMode(null)}>Cancel</Button>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {v.status === "pending" ? (
            <>
              <Button disabled={decide.isPending} onClick={() => decide.mutate({ decision: "approve" })}>Approve</Button>
              <Button variant="outline" onClick={() => setMode("reject")}>Reject</Button>
            </>
          ) : null}
          {v.status === "approved" ? <Button variant="outline" onClick={() => setMode("suspend")}>Suspend</Button> : null}
          {v.status === "suspended" ? (
            <Button variant="outline" disabled={decide.isPending} onClick={() => decide.mutate({ decision: "approve" })}>Reinstate</Button>
          ) : null}
        </div>
      )}
      {decide.error ? <p className="text-sm text-emergency">{(decide.error as Error).message}</p> : null}
    </Card>
  );
}
