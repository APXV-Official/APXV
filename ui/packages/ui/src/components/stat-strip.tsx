import type { ReactNode } from "react";
import { cn } from "../lib/utils";
import { StatusDot } from "./status-dot";

export type StatStripItem = {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "success" | "warning" | "destructive" | "muted" | "default";
};

const toneTextClass = {
  success: "text-[hsl(var(--success))]",
  warning: "text-[hsl(var(--warning))]",
  destructive: "text-[hsl(var(--destructive))]",
  muted: "text-[hsl(var(--foreground))]",
  default: "text-[hsl(var(--foreground))]",
} as const;

export function StatStrip({
  items,
  className,
}: {
  items: StatStripItem[];
  className?: string;
}) {
  return (
    <div
      className={cn(
        "grid gap-4 sm:grid-cols-2 xl:grid-cols-4",
        className,
      )}
      role="list"
      aria-label="Runtime statistics"
    >
      {items.map((item) => {
        const tone = item.tone ?? "default";
        const showDot = tone === "success" || tone === "warning" || tone === "destructive";

        return (
          <div
            key={item.label}
            role="listitem"
            className="rounded-lg border border-[hsl(var(--divider-subtle))] bg-[hsl(var(--surface))] px-5 py-4"
          >
            <p className="text-xs font-medium uppercase tracking-wide text-[hsl(var(--caption))]">
              {item.label}
            </p>
            <div className="mt-2 flex items-center gap-2">
              {showDot && (
                <StatusDot tone={tone} pulse={tone === "success"} />
              )}
              <p
                className={cn(
                  "text-xl font-semibold tracking-tight tabular-nums",
                  toneTextClass[tone],
                )}
              >
                {item.value}
              </p>
            </div>
            {item.hint && (
              <p className="mt-1.5 text-sm text-[hsl(var(--muted-foreground))]">
                {item.hint}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}