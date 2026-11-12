"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { inputCls } from "@/components/ui/field";
import { apiPage, type Schemas } from "@/lib/api";
import { cn } from "@/lib/utils";

const PRESETS = [
  { v: "", label: "All actions" },
  { v: "verification.", label: "Verification decisions" },
  { v: "referral.", label: "Referral decisions" },
  { v: "document.view", label: "Document views" },
  { v: "register.", label: "Registrations" },
  { v: "auth.login", label: "Sign-ins" },
  { v: "service.update", label: "Availability updates" },
];
const LIMIT = 50;

export default function AuditPage() {
  const [action, setAction] = useState("");
  const [since, setSince] = useState("");
  const [until, setUntil] = useState("");
  const [offset, setOffset] = useState(0);
  const qs = new URLSearchParams({ limit: String(LIMIT), offset: String(offset) });
  if (action) qs.set("action", action);
  if (since) qs.set("since", new Date(since).toISOString());
  if (until) qs.set("until", new Date(until).toISOString());

  const { data, isFetching } = useQuery({
    queryKey: ["audit", qs.toString()],
    queryFn: () => apiPage<Schemas["AuditOut"][]>(`/admin/audit?${qs.toString()}`),
    placeholderData: keepPreviousData,
  });
  const rows = data?.data ?? [];
  const total = data?.meta?.total ?? 0;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Audit log</h1>
      <Card className="flex flex-wrap items-end gap-3">
        <label className="grid gap-1 text-sm font-medium">
          Action
          <select value={action} onChange={(e) => { setAction(e.target.value); setOffset(0); }} className={cn(inputCls, "w-56")}>
            {PRESETS.map((p) => <option key={p.v} value={p.v}>{p.label}</option>)}
          </select>
        </label>
        <label className="grid gap-1 text-sm font-medium">
          From
          <input type="datetime-local" value={since} onChange={(e) => { setSince(e.target.value); setOffset(0); }} className={inputCls} />
        </label>
        <label className="grid gap-1 text-sm font-medium">
          To
          <input type="datetime-local" value={until} onChange={(e) => { setUntil(e.target.value); setOffset(0); }} className={inputCls} />
        </label>
        <span className="ml-auto text-sm text-muted-foreground">{isFetching ? "Loading…" : `${total} events`}</span>
      </Card>

      <Card className="overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead className="bg-muted text-left text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-3 py-2">When</th>
              <th className="px-3 py-2">Action</th>
              <th className="px-3 py-2">Actor</th>
              <th className="px-3 py-2">Subject</th>
              <th className="px-3 py-2">Facility</th>
              <th className="px-3 py-2">Details</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t border-border align-top">
                <td className="whitespace-nowrap px-3 py-2 tabular-nums">{new Date(r.created_at).toLocaleString()}</td>
                <td className="px-3 py-2 font-mono text-xs">{r.action}</td>
                <td className="px-3 py-2">{r.actor_name ?? r.actor_type}</td>
                <td className="px-3 py-2 text-xs">
                  {r.subject_type ? `${r.subject_type} ${r.subject_id?.slice(0, 8) ?? ""}` : "—"}
                </td>
                <td className="px-3 py-2">{r.facility_name ?? "—"}</td>
                <td className="max-w-xs px-3 py-2 text-xs text-muted-foreground">
                  {r.details ? Object.entries(r.details).filter(([k]) => k !== "verification_id")
                    .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`).join(" · ") : ""}
                </td>
              </tr>
            ))}
            {!rows.length ? (
              <tr><td colSpan={6} className="px-3 py-6 text-center text-muted-foreground">No events.</td></tr>
            ) : null}
          </tbody>
        </table>
      </Card>
      <div className="flex items-center justify-end gap-2">
        <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>Newer</Button>
        <span className="text-sm text-muted-foreground">
          {total ? `${offset + 1}–${Math.min(offset + LIMIT, total)} of ${total}` : ""}
        </span>
        <Button variant="outline" size="sm" disabled={offset + LIMIT >= total} onClick={() => setOffset(offset + LIMIT)}>Older</Button>
      </div>
    </div>
  );
}
