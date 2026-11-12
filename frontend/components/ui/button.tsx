import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

// shadcn/ui-style button in the team's "Ward" format. Minimum 56px for patient-facing sizes.
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors duration-150 disabled:opacity-50 disabled:pointer-events-none select-none",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground hover:bg-primary-strong",
        outline: "border border-[#cdd4d1] bg-card text-foreground hover:bg-muted dark:border-border",
        ghost: "text-foreground hover:bg-muted",
        emergency: "bg-emergency text-white hover:opacity-90",
        calm: "bg-calm text-calm-foreground hover:bg-calm-strong",
        mint: "bg-mint text-foreground hover:bg-mint-strong",
      },
      size: {
        sm: "h-9 px-3 text-sm",
        md: "h-11 px-4 text-base",
        lg: "min-h-14 px-5 text-lg",
        xl: "min-h-16 px-6 text-xl",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
  ),
);
Button.displayName = "Button";

export { buttonVariants };
