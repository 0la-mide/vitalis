"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ROLE_LABEL } from "@/components/admin/Charts";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/card";
import { inputCls } from "@/components/ui/field";
import { apiPage, type Schemas } from "@/lib/api";
import { cn, timeAgo } from "@/lib/utils";

const LIMIT = 50;
const STATUS_TONE: Record<string, "ok" | "warn" | "danger" | "neutral"> = {
  approved: "ok", pending: "warn", rejected: "danger", suspended: "danger",
};

export default function AccountsPage() {
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const qs = new URLSearchParams({ limit: String(LIMIT), offset: String(offset) });
  if (role) qs.set("role", role);
  if (status) qs.set("status", status);
  if (q.trim()) qs.set("q", q.trim());
  const { data, isFetching } = useQuery({
    queryKey: ["admin-accounts", qs.toString()],
    queryFn: () => apiPage<Schemas["AccountRow"][]>(`/admin/console/accounts?${qs.toString()}`),
    placeholderData: keepPreviousData,
  });
  const rows = data?.data ?? [];
  const total = data?.meta?.total ?? 0;
  const reset = () => setOffset(0);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Accounts</h1>
        <p className="text-sm text-muted-foreground">Every staff and chemist account. Patients have no accounts: they are counted on the overview.</p>
      </div>
      <Card className="flex flex-wrap items-end gap-3">
        <label className="grid gap-1 text-sm font-medium">
          Search
          <input value={q} onChange={(e) => { setQ(e.target.value); reset(); }} placeholder="Name, email, hospital, shop"
            className={cn(inputCls, "w-64")} />
        </label>
        <label className="grid gap-1 text-sm font-medium">
          Role
          <select value={role} onChange={(e) => { setRole(e.target.value); reset(); }} className={cn(inputCls, "w-48")}>
            <option value="">All roles</option>
            {Object.entries(ROLE_LABEL).map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
        </label>
        <label className="grid gap-1 text-sm font-medium">
          Status
          <select value={status} onChange={(e) => { setStatus(e.target.value); reset(); }} className={cn(inputCls, "w-40")}>
            <option value="">All</option>
            {["approved", "pending", "rejected", "suspended"].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <span className="ml-auto text-sm text-muted-foreground">{isFetching ? "Loading…" : `${total} accounts`}</span>
      </Card>

      <Card className="overflow-x-auto p-0">
        <table className="w-full text-sm">
          <thead className="bg-muted text-left text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Role</th>
              <th className="px-3 py-2">Where</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Signed up</th>
              <th className="px-3 py-2">Last sign-in</th>
              <th className="px-3 py-2 text-right">Sign-ins (30 d)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t border-border align-top">
                <td className="px-3 py-2">
                  <div className="font-medium">{r.full_name}</div>
                  <div className="text-xs text-muted-foreground">{r.email}{r.phone ? ` · ${r.phone}` : ""}</div>
                </td>
                <td className="px-3 py-2">{ROLE_LABEL[r.role] ?? r.role}</td>
                <td className="px-3 py-2">{r.facility ?? r.business ?? "—"}</td>
                <td className="px-3 py-2"><Badge tone={STATUS_TONE[r.status] ?? "neutral"}>{r.status}</Badge></td>
                <td className="whitespace-nowrap px-3 py-2 tabular-nums">{new Date(r.created_at).toLocaleDateString()}</td>
                <td className="whitespace-nowrap px-3 py-2">{r.last_login_at ? timeAgo(r.last_login_at) : "never"}</td>
                <td className="px-3 py-2 text-right tabular-nums">{r.sign_ins_30d}</td>
              </tr>
            ))}
            {!rows.length ? <tr><td colSpan={7} className="px-3 py-6 text-center text-muted-foreground">No accounts match.</td></tr> : null}
          </tbody>
        </table>
      </Card>
      <div className="flex items-center justify-end gap-2">
        <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>Previous</Button>
        <span className="text-sm text-muted-foreground">{total ? `${offset + 1}–${Math.min(offset + LIMIT, total)} of ${total}` : ""}</span>
        <Button variant="outline" size="sm" disabled={offset + LIMIT >= total} onClick={() => setOffset(offset + LIMIT)}>Next</Button>
      </div>
    </div>
  );
}
