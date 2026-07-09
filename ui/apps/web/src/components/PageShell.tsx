import { cn } from "@apxv/ui";
import type { ReactNode } from "react";
import { ConnectionBanner } from "./ConnectionBanner";

export function PageShell({
  children,
  className,
  wide,
}: {
  children: ReactNode;
  className?: string;
  wide?: boolean;
}) {
  return (
    <div
      className={cn(
        "mx-auto w-full min-w-0 space-y-8",
        wide ? "max-w-[90rem]" : "max-w-6xl",
        className,
      )}
    >
      <ConnectionBanner />
      {children}
    </div>
  );
}