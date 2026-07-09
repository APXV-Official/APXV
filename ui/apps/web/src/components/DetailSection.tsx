import type { ReactNode } from "react";

export function DetailSection({
  title,
  children,
  defaultOpen = true,
}: {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  return (
    <details
      open={defaultOpen}
      className="group rounded-lg bg-[hsl(var(--overlay-subtle))]"
    >
      <summary className="cursor-pointer list-none px-5 py-4 text-sm font-semibold tracking-wide text-[hsl(var(--foreground))] marker:content-none [&::-webkit-details-marker]:hidden">
        <span className="flex items-center justify-between gap-2">
          {title}
          <span className="text-xs font-normal text-[hsl(var(--muted-foreground))] group-open:hidden">
            Show
          </span>
        </span>
      </summary>
      <div className="border-t border-[hsl(var(--divider-subtle))] px-5 py-5">{children}</div>
    </details>
  );
}