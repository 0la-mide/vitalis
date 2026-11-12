import * as React from "react";
import { cn } from "@/lib/utils";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-lg border border-border bg-card p-4", className)} {...props} />;
}

// Ward badges: soft fill + inset ring; colour carries meaning, text always says it too.
const BADGE_TONES = {
  neutral: "bg-muted text-muted-foreground ring-border",
  ok: "bg-mint text-primary-strong ring-mint-strong",
  warn: "bg-warning-soft text-warning ring-warning/20",
  danger: "bg-emergency-soft text-emergency ring-emergency/20",
  info: "bg-info-soft text-info ring-info/20",
  ai: "bg-ai-soft text-ai ring-ai/20",
} as const;

export function Badge({
  tone = "neutral",
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: keyof typeof BADGE_TONES }) {
  return (
    <span
      className={cn(
        "inline-flex h-6 items-center gap-1 rounded-md px-2 text-xs font-semibold whitespace-nowrap ring-1 ring-inset",
        BADGE_TONES[tone],
        className,
      )}
      {...props}
    />
  );
}
