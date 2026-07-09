import type { ReactNode } from "react";
import { cn } from "../lib/utils";

export function MetricCard({
  label,
  value,
  hint,
  icon,
  className,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-2xl bg-[hsl(var(--surface-elevated))] p-6 ring-1 ring-[hsl(var(--ring-border))] shadow-[0_1px_2px_hsl(var(--shadow-color))]",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-[hsl(var(--muted-foreground))]">
            {label}
          </p>
          <p className="mt-2 text-3xl font-semibold tracking-tight tabular-nums text-[hsl(var(--foreground))]">
            {value}
          </p>
          {hint && (
            <p className="mt-2 text-sm text-[hsl(var(--muted-foreground))]">
              {hint}
            </p>
          )}
        </div>
        {icon && (
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[hsl(var(--primary-muted)/0.14)] text-[hsl(var(--primary))] ring-1 ring-[hsl(var(--primary)/0.18)]">
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}