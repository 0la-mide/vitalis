"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge, Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { HOSPITAL_ROLES, ROLE_LABEL, useMe } from "@/lib/staff";

const STATUS_COPY: Record<string, string> = {
  pending: "Your account is waiting for verification. You will be able to work once it is approved.",
  rejected: "Your registration was not approved. See the reason below; you can correct it and resubmit.",
  suspended: "Your account is suspended. Contact your facility admin or the VITALIS network admin.",
  approved: "Your account is approved.",
};

export default function StatusPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { data: me, error } = useMe();

  const logout = async () => {
    await api("/auth/logout", { method: "POST" }).catch(() => {});
    qc.clear();
    router.replace("/auth/login");
  };

  if (error) {
    return (
      <main className="p-6 text-center">
        <p>Please sign in.</p>
        <Button className="mt-3" onClick={() => router.replace("/auth/login")}>
          Sign in
        </Button>
      </main>
    );
  }
  if (!me) return <main className="p-6 text-center text-muted-foreground">Loading…</main>;

  const facilityPending = me.facility && me.facility.status !== "approved";
  const tone = me.status === "approved" && !facilityPending ? "ok" : me.status === "pending" ? "warn" : "danger";
  return (
    <main className="mx-auto w-full max-w-md px-4 py-10">
      <Card>
        <h1 className="text-xl font-bold">{me.full_name}</h1>
        <p className="text-sm text-muted-foreground">
          {ROLE_LABEL[me.role] ?? me.role}
          {me.facility ? ` · ${me.facility.name}` : ""}
        </p>
        <div className="mt-3 flex gap-2">
          <Badge tone={tone}>Account: {me.status}</Badge>
          {me.facility ? (
            <Badge tone={me.facility.status === "approved" ? "ok" : "warn"}>Facility: {me.facility.status}</Badge>
          ) : null}
        </div>
        <p className="mt-3">
          {facilityPending ? "Your facility is waiting for verification by the VITALIS network admin." : STATUS_COPY[me.status]}
        </p>
        {me.status_reason ? <p className="mt-2 rounded-lg bg-muted p-2 text-sm">Reason: {me.status_reason}</p> : null}
        {me.status === "approved" && !facilityPending && !HOSPITAL_ROLES.includes(me.role) ? (
          <p className="mt-3 rounded-lg bg-mint p-2 text-sm">
            The {ROLE_LABEL[me.role]?.toLowerCase()} workspace is coming in the next build phase.
          </p>
        ) : null}
        <div className="mt-4 flex gap-2">
          {me.status === "approved" && !facilityPending && HOSPITAL_ROLES.includes(me.role) ? (
            <Button onClick={() => router.push("/hospital")}>Open hospital screen</Button>
          ) : null}
          <Button variant="outline" onClick={logout}>
            Sign out
          </Button>
        </div>
      </Card>
    </main>
  );
}
