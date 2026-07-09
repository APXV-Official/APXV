import type { ReactNode } from "react";
import { cn } from "../lib/utils";

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-2xl bg-[hsl(var(--overlay-subtle))] px-10 py-16 text-center ring-1 ring-[hsl(var(--divider-subtle))]",
        className,
      )}
    >
      {icon && (
        <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-[hsl(var(--overlay))] text-[hsl(var(--muted-foreground))] ring-1 ring-[hsl(var(--ring-border))]">
          {icon}
        </div>
      )}
      <p className="text-base font-semibold text-[hsl(var(--foreground))]">{title}</p>
      {description && (
        <p className="mt-2 max-w-md text-[0.9375rem] leading-relaxed text-[hsl(var(--muted-foreground))]">
          {description}
        </p>
      )}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}