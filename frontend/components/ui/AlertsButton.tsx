"use client";

import { Bell, BellOff, BellRing } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { enablePush, pushState, syncPush, testPush, type PushState } from "@/lib/push";
import { cn } from "@/lib/utils";

/** "Get alerts on this phone": web push, so news reaches people even when VITALIS is closed. */
export function AlertsButton({ who, className }: { who: "patient" | "staff"; className?: string }) {
  const [state, setState] = useState<PushState | null>(null);
  const [busy, setBusy] = useState(false);
  const [test, setTest] = useState<string | null>(null);
  useEffect(() => {
    // A phone that already said yes is re-registered quietly, so the server always has it, for whoever is using it now.
    void pushState().then((s) => {
      setState(s);
      if (s === "on") void syncPush(who).then(setState);
    });
  }, [who]);

  if (!state || state === "unsupported") return null;
  if (state === "on") {
    return (
      <span className={cn("inline-flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-medium text-primary", className)}>
        <span className="inline-flex items-center gap-1.5"><BellRing className="size-4" /> Alerts on for this phone</span>
        <button
          type="button"
          disabled={busy}
          className="text-xs font-normal text-muted-foreground underline underline-offset-2"
          onClick={async () => {
            setBusy(true);
            setTest(null);
            try {
              const n = await testPush(who);
              setTest(n ? "Test alert sent. It should arrive in a few seconds." : "This phone isn't registered yet. Reload and try again.");
            } catch {
              setTest("Could not send a test alert. Check the connection.");
            } finally {
              setBusy(false);
            }
          }}
        >
          Send a test alert
        </button>
        {test ? <span className="w-full text-xs font-normal text-muted-foreground">{test}</span> : null}
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
      } catch {
        setState(await pushState());
      } finally {
        setBusy(false);
      }
    }}>
      <Bell className="size-4" /> {busy ? "Turning on…" : "Get alerts on this phone"}
    </Button>
  );
}
