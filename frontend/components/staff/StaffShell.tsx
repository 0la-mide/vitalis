"use client";

import { useQueryClient } from "@tanstack/react-query";
import { LogOut } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { ROLE_LABEL } from "@/lib/staff";
import { cn } from "@/lib/utils";

export type NavItem = { href: string; label: string; icon: React.ReactNode; exact?: boolean };

/** VITALIS mark (pulse line), same as the team's NCS frontend. */
export function Logo({ subtitle = "Health record network" }: { subtitle?: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="grid size-8 place-items-center rounded-md bg-primary text-primary-foreground">
        <svg viewBox="0 0 64 64" className="size-5" aria-hidden>
          <path d="M6 34h12l5-12 9 24 6-16 4 4h16" fill="none" stroke="currentColor" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <div className="leading-tight">
        <div className="text-base font-bold tracking-tight">VITALIS</div>
        <div className="text-xs text-muted-foreground">{subtitle}</div>
      </div>
    </div>
  );
}

const JOURNEY = [
  { roles: ["receptionist", "facility_admin"], label: "Reception", hint: "Referrals and check-in" },
  { roles: ["nurse"], label: "Nursing", hint: "Record vital signs" },
  { roles: ["doctor"], label: "Doctor", hint: "Review history, decide" },
  { roles: ["lab"], label: "Lab & imaging", hint: "Results back to doctor" },
];

/** Staff layout in the team's "Ward" format: sidebar on desktop, compact top bar on phones. */
export function StaffShell({
  nav,
  user,
  title,
  showJourney,
  children,
}: {
  nav: NavItem[];
  user?: { full_name: string; role: string; facility?: { name: string } | null } | null;
  title?: string;
  showJourney?: boolean;
  children: React.ReactNode;
}) {
  const path = usePathname();
  const router = useRouter();
  const qc = useQueryClient();
  const isActive = (n: NavItem) => (n.exact ? path === n.href : path === n.href || path.startsWith(`${n.href}/`));
  const step = user ? JOURNEY.findIndex((j) => j.roles.includes(user.role)) : -1;
  const signOut = async () => {
    await api("/auth/logout", { method: "POST" }).catch(() => {});
    qc.clear();
    router.replace("/auth/login");
  };

  return (
    <div className="flex min-h-full flex-1">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-border bg-card lg:flex">
        <div className="px-5 py-5"><Logo /></div>
        <nav className="flex-1 space-y-1 px-3" aria-label="Main">
          {nav.map((n) => (
            <Link key={n.href} href={n.href}
              className={cn("flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors [&>svg]:size-[18px]",
                isActive(n) ? "bg-mint text-primary-strong" : "text-muted-foreground hover:bg-muted hover:text-foreground")}>
              {n.icon}
              {n.label}
            </Link>
          ))}
          {showJourney && step >= 0 ? (
            <div className="pt-8">
              <div className="px-3 pb-3 text-xs font-semibold text-muted-foreground">Patient journey</div>
              <ol className="space-y-0.5 px-3">
                {JOURNEY.map((j, i) => (
                  <li key={j.label} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <span className={cn("grid size-6 place-items-center rounded-full text-xs font-semibold",
                        i === step ? "bg-primary text-primary-foreground" : i < step ? "bg-mint-strong text-primary-strong" : "bg-muted text-muted-foreground")}>
                        {i + 1}
                      </span>
                      {i < JOURNEY.length - 1 ? <span className="my-0.5 h-5 w-px bg-border" /> : null}
                    </div>
                    <div className="pt-0.5">
                      <div className={cn("text-sm", i === step ? "font-semibold" : "text-muted-foreground")}>{j.label}</div>
                      {i === step ? <div className="text-xs text-muted-foreground">{j.hint}</div> : null}
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          ) : null}
        </nav>
        {user ? (
          <div className="border-t border-border p-3">
            <div className="flex items-center gap-3 px-2 py-2">
              <span className="grid size-9 shrink-0 place-items-center rounded-full bg-mint text-sm font-semibold text-primary-strong">
                {user.full_name.replace(/\(.*?\)/g, "").trim().split(/\s+/).map((x) => x[0]).slice(0, 2).join("").toUpperCase()}
              </span>
              <div className="min-w-0 flex-1 leading-tight">
                <div className="truncate text-sm font-semibold">{user.full_name}</div>
                <div className="truncate text-xs text-muted-foreground">
                  {ROLE_LABEL[user.role] ?? user.role}{user.facility ? ` · ${user.facility.name}` : ""}
                </div>
              </div>
              <button type="button" aria-label="Sign out" onClick={signOut} className="rounded-md p-1.5 text-muted-foreground hover:bg-muted">
                <LogOut className="size-[18px]" />
              </button>
            </div>
          </div>
        ) : null}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Phones / tablets */}
        <header className="sticky top-0 z-30 border-b border-border bg-card lg:hidden">
          <div className="flex items-center gap-3 px-4 py-2">
            <Logo subtitle={title ?? user?.facility?.name ?? "VITALIS"} />
            <div className="flex-1" />
            <button type="button" aria-label="Sign out" onClick={signOut} className="rounded-md p-2 hover:bg-muted"><LogOut className="h-5 w-5" /></button>
          </div>
          <nav className="flex gap-1 overflow-x-auto px-3 pb-2">
            {nav.map((n) => (
              <Link key={n.href} href={n.href}
                className={cn("whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-semibold",
                  isActive(n) ? "bg-mint text-primary-strong" : "text-muted-foreground hover:bg-muted")}>
                {n.label}
              </Link>
            ))}
          </nav>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-5 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
