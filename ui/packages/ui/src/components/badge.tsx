import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "../lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        default:
          "bg-[hsl(var(--primary)/0.18)] text-[hsl(var(--primary))]",
        secondary:
          "bg-[hsl(var(--overlay-muted))] text-[hsl(var(--muted-foreground))]",
        success:
          "bg-[hsl(var(--success)/0.12)] text-[hsl(var(--success))]",
        warning:
          "bg-[hsl(var(--warning)/0.12)] text-[hsl(var(--warning))]",
        destructive:
          "bg-[hsl(var(--destructive)/0.12)] text-[hsl(var(--destructive))]",
        outline:
          "bg-transparent text-[hsl(var(--muted-foreground))]",
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

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}