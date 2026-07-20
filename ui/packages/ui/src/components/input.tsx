import * as React from "react";
import { cn } from "../lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", ...props }, ref) => (
    <input
      type={type}
      className={cn(
        "flex h-9 w-full rounded-md border border-[hsl(var(--divider-subtle))] bg-[hsl(var(--input-bg))] px-3 py-1.5 text-sm text-[hsl(var(--foreground))] transition-colors duration-150",
        "placeholder:text-[hsl(var(--muted-foreground))]",
        "hover:border-[hsl(var(--divider))]",
        "focus-visible:border-[hsl(var(--primary))] focus-visible:outline-none focus-visible:ring-0",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      ref={ref}
      {...props}
    />
  ),
);
Input.displayName = "Input";