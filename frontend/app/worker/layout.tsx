"use client";

import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { useQueryClient } from "@tanstack/react-query";
import { LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useRequireWorker } from "@/lib/staff";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/worker", label: "New walk-in" },
  { href: "/worker/referrals", label: "My referrals" },
];

export default function WorkerLayout({ children }: { children: React.ReactNode }) {
  const { data: me } = useRequireWorker();
  const path = usePathname();
  const router = useRouter();
  const qc = useQueryClient();
  const ready = me?.role === "worker" && me.status === "approved";
  const inTriage = path === "/worker/triage";
  return (
    <div className="flex min-h-full flex-1 flex-col">
      {!inTriage ? (
        <header className="sticky top-0 z-30 border-b border-border bg-card">
          <div className="mx-auto flex max-w-md items-center gap-3 px-4 py-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/icons/icon-192.png" alt="" className="h-8 w-8 rounded-lg" />
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-bold">{me?.full_name ?? "VITALIS"}</div>
              <div className="text-xs text-muted-foreground">Frontline worker</div>
            </div>
            <ThemeToggle />
            <button type="button" aria-label="Sign out" className="rounded-lg p-2 hover:bg-muted"
              onClick={async () => {
                await api("/auth/logout", { method: "POST" }).catch(() => {});
                qc.clear();
                router.replace("/auth/login");
              }}>
              <LogOut className="h-5 w-5" />
            </button>
          </div>
          <nav className="mx-auto grid max-w-md grid-cols-2 gap-1 px-4 pb-2">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href}
                className={cn("rounded-lg py-2 text-center text-sm font-semibold",
                  path === n.href ? "bg-mint text-primary-strong" : "bg-muted")}>
                {n.label}
              </Link>
            ))}
          </nav>
        </header>
      ) : null}
      {ready ? children : <p className="p-6 text-center text-muted-foreground">Loading…</p>}
    </div>
  );
}
