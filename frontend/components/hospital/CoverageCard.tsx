"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { HeartHandshake, ShieldCheck } from "lucide-react";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useMe } from "@/lib/staff";
import { cn } from "@/lib/utils";

type Coverage = { accepts_nhia: boolean; free_maternal_care: boolean };

/** Cost and coverage families see on this hospital's card. Hospital admins set it; everyone else sees it. */
export function CoverageCard() {
  const qc = useQueryClient();
  const { data: me } = useMe();
  const canEdit = me?.role === "facility_admin";
  const { data } = useQuery({ queryKey: ["coverage"], queryFn: () => api<Coverage>("/hospital/coverage") });
  const save = useMutation({
    mutationFn: (c: Coverage) => api<Coverage>("/hospital/coverage", { method: "PUT", body: c }),
    onSuccess: (c) => qc.setQueryData(["coverage"], c),
  });
  if (!data) return null;
  const rows = [
    { key: "accepts_nhia" as const, icon: ShieldCheck, title: "Accepts NHIA patients", hint: "National Health Insurance Authority, formerly the NHIS" },
    { key: "free_maternal_care" as const, icon: HeartHandshake, title: "Free maternal and child care", hint: "A state programme covers pregnancy and young children here" },
  ];
  return (
    <Card className="space-y-2">
      <h2 className="font-bold">Cost and coverage</h2>
      <p className="text-sm text-muted-foreground">Shown to families on your hospital&apos;s card. Insured patients see you a little higher in the list.</p>
      {rows.map(({ key, icon: Icon, title, hint }) => (
        <label key={key} className={cn("flex items-center gap-3 rounded-lg border border-border p-3", canEdit && "cursor-pointer hover:bg-muted")}>
          <Icon className="h-5 w-5 shrink-0 text-primary" />
          <span className="flex-1"><b className="block">{title}</b><span className="text-sm text-muted-foreground">{hint}</span></span>
          <input type="checkbox" className="h-5 w-5" checked={data[key]} disabled={!canEdit || save.isPending}
            onChange={(e) => save.mutate({ ...data, [key]: e.target.checked })} aria-label={title} />
        </label>
      ))}
      {!canEdit ? <p className="text-xs text-muted-foreground">Only the hospital admin can change this.</p> : null}
    </Card>
  );
}
