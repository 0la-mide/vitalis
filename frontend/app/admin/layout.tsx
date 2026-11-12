"use client";

import { BadgeCheck, LayoutDashboard, ScrollText } from "lucide-react";
import { StaffShell, type NavItem } from "@/components/staff/StaffShell";
import { useRequireNetworkAdmin } from "@/lib/staff";

const NAV: NavItem[] = [
  { href: "/admin", label: "Network overview", icon: <LayoutDashboard />, exact: true },
  { href: "/admin/verifications", label: "Verifications", icon: <BadgeCheck /> },
  { href: "/admin/audit", label: "Audit & governance", icon: <ScrollText /> },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { data: me } = useRequireNetworkAdmin();
  const ready = me?.role === "network_admin" && me.status === "approved";
  return (
    <StaffShell nav={NAV} user={me} title="Network admin">
      {ready ? children : <p className="text-muted-foreground">Loading…</p>}
    </StaffShell>
  );
}
