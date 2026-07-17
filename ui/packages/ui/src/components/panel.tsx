import type { ReactNode } from "react";
import { cn } from "../lib/utils";

/** Open surface — spacing over borders. */
export function Panel({
  children,
  className,
  ...props
}: React.ComponentPropsWithoutRef<"section">) {
  return (
    <section
      className={cn(
        "rounded-2xl bg-[hsl(var(--surface))] ring-1 ring-[hsl(var(--ring-border))] shadow-[0_1px_2px_hsl(var(--shadow-color))]",
        className,
      )}
      {...props}
    >
      {children}
    </section>
  );
}

export function PanelHeader({
  title,
  description,
  actions,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-start justify-between gap-4 px-6 pb-3 pt-6",
        className,
      )}
    >
      <div className="min-w-0">
        <h2 className="text-lg font-semibold tracking-tight text-[hsl(var(--foreground))]">
          {title}
        </h2>
        {description && (
          <p className="mt-1 text-[0.9375rem] leading-relaxed text-[hsl(var(--muted-foreground))]">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

export function PanelBody({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn("px-6 pb-6", className)}>{children}</div>;
}