"use client";

import { AlertsButton } from "@/components/ui/AlertsButton";
import { Radio } from "lucide-react";
import { RecentReferrals, useWorkerReferrals } from "@/components/worker/referrals";
import { cn } from "@/lib/utils";

export default function MyReferralsPage() {
  const { live } = useWorkerReferrals();
  return (
    <main className="mx-auto w-full max-w-md space-y-3 px-4 py-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">My referrals</h1>
        <span className={cn("inline-flex items-center gap-1 text-sm", live ? "text-primary" : "text-muted-foreground")}>
          <Radio className={cn("h-4 w-4", live && "vt-pulse")} aria-hidden /> {live ? "Live" : "Connecting…"}
        </span>
      </div>
      <AlertsButton who="staff" />
      <RecentReferrals />
    </main>
  );
}
