"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useSyncExternalStore } from "react";
import { cn } from "@/lib/utils";

type Theme = "light" | "dark";
const KEY = "vitalis-theme";

function apply(t: Theme) {
  document.documentElement.dataset.theme = t;
}

// The theme lives on <html data-theme>; layout.tsx sets it before first paint.
function subscribe(cb: () => void) {
  const mo = new MutationObserver(cb);
  mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => mo.disconnect();
}
const read = (): Theme => (document.documentElement.dataset.theme === "dark" ? "dark" : "light");

/** Sun/moon switch. Same calm palette in both modes; the choice is remembered on this phone. */
export function ThemeToggle({ className }: { className?: string }) {
  const theme = useSyncExternalStore(subscribe, read, () => "light" as Theme);

  // Until the user picks, follow the phone's setting live.
  useEffect(() => {
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const follow = () => {
      let saved: string | null = null;
      try { saved = localStorage.getItem(KEY); } catch {}
      if (saved !== "light" && saved !== "dark") apply(mq.matches ? "dark" : "light");
    };
    mq.addEventListener("change", follow);
    return () => mq.removeEventListener("change", follow);
  }, []);

  const next: Theme = theme === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode`}
      onClick={() => {
        apply(next);
        try { localStorage.setItem(KEY, next); } catch {}
      }}
      className={cn("grid size-10 place-items-center rounded-full text-muted-foreground hover:bg-muted", className)}
    >
      {theme === "dark" ? <Sun className="size-5" /> : <Moon className="size-5" />}
    </button>
  );
}
