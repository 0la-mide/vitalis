"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { IdCard, Pencil } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { inputCls } from "@/components/ui/field";
import { api, type Schemas } from "@/lib/api";
import { cn } from "@/lib/utils";

type P = { vitalis_id: string; name?: string | null; nhia_number?: string | null };

/** The patient's name when known, always with the VITALIS ID (the ID is what links every visit). */
export function PatientName({ p, size = "md" }: { p: P; size?: "sm" | "md" | "lg" }) {
  const big = size === "lg" ? "text-2xl" : size === "md" ? "text-lg" : "text-base";
  return p.name ? (
    <span className="inline-flex flex-wrap items-baseline gap-x-2">
      <span className={cn("font-bold", big)}>{p.name}</span>
      <span className="font-mono text-sm text-muted-foreground">{p.vitalis_id}</span>
    </span>
  ) : (
    <span className={cn("font-mono font-bold", big)}>{p.vitalis_id}</span>
  );
}

/** Reception, nurses and hospital admins record or correct the name and NHIA number. */
export function IdentityCard({ encounterId, p, canEdit }: { encounterId: string; p: P; canEdit: boolean }) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const save = useMutation({
    mutationFn: (body: { full_name: string; nhia_number: string }) =>
      api<Schemas["EncounterOut"]>(`/hospital/encounters/${encounterId}/patient`, { method: "PATCH", body }),
    onSuccess: (e) => {
      qc.setQueryData(["encounter", encounterId], e);
      setEditing(false);
    },
  });
  return (
    <Card className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-bold"><IdCard className="size-5 text-muted-foreground" />Patient details</h2>
        {canEdit && !editing ? <Button size="sm" variant="outline" onClick={() => setEditing(true)}><Pencil className="size-4" />Edit</Button> : null}
      </div>
      {editing ? (
        <form className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]" onSubmit={(ev) => {
          ev.preventDefault();
          const fd = new FormData(ev.currentTarget);
          save.mutate({ full_name: String(fd.get("full_name") ?? ""), nhia_number: String(fd.get("nhia_number") ?? "") });
        }}>
          <input name="full_name" defaultValue={p.name ?? ""} placeholder="Full name" maxLength={120} className={inputCls} aria-label="Full name" />
          <input name="nhia_number" defaultValue={p.nhia_number ?? ""} placeholder="NHIA number (optional)" maxLength={24} className={inputCls} aria-label="NHIA number" />
          <Button type="submit" disabled={save.isPending}>Save</Button>
          {save.error ? <p className="text-sm text-emergency sm:col-span-3">{(save.error as Error).message}</p> : null}
        </form>
      ) : (
        <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-3">
          <div><dt className="text-muted-foreground">Name</dt><dd className="font-semibold">{p.name ?? "Not recorded"}</dd></div>
          <div><dt className="text-muted-foreground">VITALIS ID</dt><dd className="font-mono">{p.vitalis_id}</dd></div>
          <div><dt className="text-muted-foreground">NHIA (formerly NHIS)</dt><dd className="font-mono">{p.nhia_number ?? "—"}</dd></div>
        </dl>
      )}
    </Card>
  );
}
