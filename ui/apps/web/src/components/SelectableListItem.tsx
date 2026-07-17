import { Badge } from "@apxv/ui";
import type { ReactNode } from "react";

export function SelectableListItem({
  selected,
  onClick,
  title,
  subtitle,
  badge,
  meta,
}: {
  selected: boolean;
  onClick: () => void;
  title: ReactNode;
  subtitle?: ReactNode;
  badge?: ReactNode;
  meta?: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-selected={selected}
      className={[
        "w-full cursor-pointer rounded-lg px-5 py-4 text-left transition-colors",
        selected
          ? "bg-[hsl(var(--overlay-subtle))] shadow-[inset_3px_0_0_0_hsl(var(--primary))]"
          : "hover:bg-[hsl(var(--overlay-subtle))]",
      ].join(" ")}
    >
      <p className="text-[0.9375rem] font-medium leading-snug text-[hsl(var(--foreground))]">
        {title}
      </p>
      {subtitle && (
        <p className="mt-1.5 truncate font-mono text-sm text-[hsl(var(--muted-foreground))]">
          {subtitle}
        </p>
      )}
      {(badge || meta) && (
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
          {badge}
          {meta && (
            <span className="text-sm text-[hsl(var(--muted-foreground))]">{meta}</span>
          )}
        </div>
      )}
    </button>
  );
}

export function SelectableListBadge({
  children,
  variant = "secondary",
}: {
  children: ReactNode;
  variant?: "default" | "secondary" | "success" | "warning" | "destructive";
}) {
  return (
    <Badge variant={variant} className="text-xs font-normal">
      {children}
    </Badge>
  );
}