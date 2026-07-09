import type { ReactNode } from "react";
import { cn } from "../lib/utils";

/** Horizontal group for related actions — consistent spacing and wrap. */
export function ActionGroup({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-7 gap-y-3",
        className,
      )}
      role="group"
    >
      {children}
    </div>
  );
}

/** Toolbar row: status/meta on the left, actions on the right. */
export function PageToolbar({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center justify-between gap-x-8 gap-y-4 border-b border-[hsl(var(--divider-subtle))] pb-6",
        className,
      )}
    >
      {children}
    </div>
  );
}