import * as React from "react";
import { cn } from "../lib/utils";

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...props }, ref) => (
    <select
      className={cn(
        "h-10 min-w-[10rem] appearance-none rounded-lg border border-[hsl(var(--divider-subtle))] bg-[hsl(var(--input-bg))] px-4 pr-10 text-sm text-[hsl(var(--foreground))] transition-colors duration-150",
        "hover:border-[hsl(var(--divider))]",
        "focus-visible:border-[hsl(var(--primary))] focus-visible:outline-none focus-visible:ring-0",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      ref={ref}
      {...props}
    >
      {children}
    </select>
  ),
);
Select.displayName = "Select";