"use client";

import { BedDouble, ClipboardList, FlaskConical, Inbox, ShieldCheck, ToggleRight } from "lucide-react";
import { StaffShell, type NavItem } from "@/components/staff/StaffShell";
import { useRequireHospitalStaff } from "@/lib/staff";

export default function HospitalLayout({ children }: { children: React.ReactNode }) {
  const { data: me } = useRequireHospitalStaff();
  const ready = me && me.status === "approved" && me.facility?.status === "approved";
  const role = me?.role ?? "";
  const nav: NavItem[] = [
    { href: "/hospital", label: "Incoming referrals", icon: <Inbox />, exact: true },
    { href: "/hospital/patients", label: "Patients in the facility", icon: <BedDouble /> },
    ...(role === "lab" || role === "radiology" ? [{ href: "/hospital/lab", label: role === "lab" ? "Lab worklist" : "Radiology worklist", icon: <FlaskConical /> }] : []),
    { href: "/hospital/availability", label: "Service availability", icon: <ToggleRight /> },
    ...(role === "facility_admin" ? [{ href: "/hospital/staff", label: "Staff approvals", icon: <ShieldCheck /> }] : []),
  ];
  return (
    <StaffShell nav={nav} user={me} title={me?.facility?.name} showJourney>
      {ready ? children : <p className="text-muted-foreground"><ClipboardList className="mr-2 inline h-4 w-4" />Loading…</p>}
    </StaffShell>
  );
}
