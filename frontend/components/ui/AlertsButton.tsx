"use client";

import { Bell, BellOff, BellRing } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { enablePush, pushState, type PushState } from "@/lib/push";
import { cn } from "@/lib/utils";

/** "Get alerts on this phone": web push, so news reaches people even when VITALIS is closed. */
export function AlertsButton({ who, className }: { who: "patient" | "staff"; className?: string }) {
  const [state, setState] = useState<PushState | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    void pushState().then(setState);
  }, []);

  if (!state || state === "unsupported") return null;
  if (state === "on") {
    return (
      <span className={cn("inline-flex items-center gap-1.5 text-sm font-medium text-primary", className)}>
        <BellRing className="size-4" /> Alerts on for this phone
      </span>
    );
  }
  if (state === "denied") {
    return (
      <span className={cn("inline-flex items-center gap-1.5 text-sm text-muted-foreground", className)}>
        <BellOff className="size-4" /> Alerts are blocked in this browser&apos;s settings
      </span>
    );
  }
  if (state === "needs-install") {
    return (
      <p className={cn("text-sm text-muted-foreground", className)}>
        <Bell className="mr-1 inline size-4" />For alerts on iPhone: tap Share, then <b>Add to Home Screen</b>, and open VITALIS from there.
      </p>
    );
  }
  return (
    <Button variant="outline" size="sm" disabled={busy} className={className} onClick={async () => {
      setBusy(true);
      try {
        setState(await enablePush(who));
      } finally {
        setBusy(false);
      }
    }}>
      <Bell className="size-4" /> {busy ? "Turning on…" : "Get alerts on this phone"}
    </Button>
  );
}
