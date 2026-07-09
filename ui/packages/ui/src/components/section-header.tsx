import type { ReactNode } from "react";
import { cn } from "../lib/utils";

export function SectionHeader({
  title,
  action,
  className,
}: {
  title: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-x-8 sm:gap-y-4",
        className,
      )}
    >
      <h2 className="min-w-0 text-base font-semibold tracking-tight text-[hsl(var(--foreground))]">
        {title}
      </h2>
      {action && (
        <div className="flex min-w-0 max-w-full flex-wrap items-center gap-x-7 gap-y-3 sm:justify-end">
          {action}
        </div>
      )}
    </div>
  );
}