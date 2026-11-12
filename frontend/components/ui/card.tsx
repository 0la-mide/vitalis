import * as React from "react";
import { cn } from "@/lib/utils";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-2xl border border-border bg-card p-4 shadow-sm", className)} {...props} />;
}

const BADGE_TONES = {
  neutral: "bg-muted text-muted-foreground",
  ok: "bg-mint text-primary-strong",
  warn: "bg-warning-soft text-warning",
  danger: "bg-emergency-soft text-emergency",
  info: "bg-primary text-primary-foreground",
} as const;

export function Badge({
  tone = "neutral",
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: keyof typeof BADGE_TONES }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap",
        BADGE_TONES[tone],
        className,
      )}
      {...props}
    />
  );
}
