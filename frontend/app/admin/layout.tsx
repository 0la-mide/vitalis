"use client";

import { useQueryClient } from "@tanstack/react-query";
import { LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useRequireNetworkAdmin } from "@/lib/staff";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/admin", label: "Overview" },
  { href: "/admin/verifications", label: "Verifications" },
  { href: "/admin/audit", label: "Audit log" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { data: me } = useRequireNetworkAdmin();
  const path = usePathname();
  const router = useRouter();
  const qc = useQueryClient();
  const ready = me?.role === "network_admin" && me.status === "approved";
  return (
    <div className="flex min-h-full flex-1 flex-col bg-muted">
      <header className="sticky top-0 z-30 border-b border-border bg-card">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/icons/icon-192.png" alt="" className="h-8 w-8 rounded-lg" />
          <div className="min-w-0 flex-1">
            <div className="font-bold">VITALIS network admin</div>
            <div className="truncate text-xs text-muted-foreground">{me?.full_name}</div>
          </div>
          <nav className="flex gap-1">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href}
                className={cn("rounded-lg px-3 py-2 text-sm font-semibold",
                  path === n.href ? "bg-mint text-primary-strong" : "hover:bg-muted")}>
                {n.label}
              </Link>
            ))}
          </nav>
          <button type="button" aria-label="Sign out" className="rounded-lg p-2 hover:bg-muted"
            onClick={async () => {
              await api("/auth/logout", { method: "POST" }).catch(() => {});
              qc.clear();
              router.replace("/auth/login");
            }}>
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-4">
        {ready ? children : <p className="text-muted-foreground">Loading…</p>}
      </main>
    </div>
  );
}
