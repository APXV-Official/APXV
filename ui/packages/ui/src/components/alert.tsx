import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "../lib/utils";

const alertVariants = cva(
  "relative w-full rounded-xl px-6 py-5 text-base ring-1 [&>p]:leading-relaxed",
  {
    variants: {
      variant: {
        default:
          "bg-[hsl(var(--surface))] text-[hsl(var(--foreground))] ring-[hsl(var(--ring-border))]",
        destructive:
          "bg-[hsl(var(--destructive)/0.1)] text-[hsl(var(--foreground))] ring-[hsl(var(--destructive)/0.28)]",
        warning:
          "bg-[hsl(var(--warning)/0.1)] text-[hsl(var(--foreground))] ring-[hsl(var(--warning)/0.28)]",
        success:
          "bg-[hsl(var(--success)/0.1)] text-[hsl(var(--foreground))] ring-[hsl(var(--success)/0.28)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {}

export function Alert({ className, variant, ...props }: AlertProps) {
  return (
    <div
      role="alert"
      className={cn(alertVariants({ variant }), className)}
      {...props}
    />
  );
}

export function AlertTitle({
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={cn("mb-1.5 text-base font-semibold leading-snug tracking-tight", className)}
      {...props}
    />
  );
}

export function AlertDescription({
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={cn("text-[0.9375rem] leading-relaxed text-[hsl(var(--muted-foreground))]", className)}
      {...props}
    />
  );
}