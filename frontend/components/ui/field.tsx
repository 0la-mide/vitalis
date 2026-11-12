import * as React from "react";
import { cn } from "@/lib/utils";

export const inputCls =
  "h-11 w-full rounded-lg border border-border bg-card px-3 text-base outline-none focus:border-primary";

export function Field({
  label,
  hint,
  children,
  className,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <label className={cn("grid gap-1 text-sm font-medium", className)}>
      {label}
      {children}
      {hint ? <span className="text-xs font-normal text-muted-foreground">{hint}</span> : null}
    </label>
  );
}
