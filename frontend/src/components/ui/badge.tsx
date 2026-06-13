import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide",
  {
    variants: {
      variant: {
        default: "bg-bg-overlay text-fg-muted border border-white/10",
        outcomeHome: "bg-outcome-home/20 text-outcome-home border border-outcome-home/30",
        outcomeDraw: "bg-outcome-draw/20 text-outcome-draw border border-outcome-draw/30",
        outcomeAway: "bg-outcome-away/20 text-outcome-away border border-outcome-away/30",
        edge: "gradient-edge text-bg-base border border-amber-600/30",
        live: "bg-brand-danger/20 text-brand-danger border border-brand-danger/30 animate-pulse",
        success: "bg-brand-primary/20 text-brand-primary border border-brand-primary/30",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
