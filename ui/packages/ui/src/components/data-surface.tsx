import type { ReactNode } from "react";
import { cn } from "../lib/utils";

/** Open canvas for lists and tables — no card chrome. */
export function DataSurface({
  children,
  className,
  padded = false,
}: {
  children: ReactNode;
  className?: string;
  padded?: boolean;
}) {
  return (
    <div className={cn(padded && "px-1", className)}>{children}</div>
  );
}