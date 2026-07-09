import * as React from "react";
import { cn } from "../lib/utils";

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => (
    <textarea
      className={cn(
        "flex min-h-[120px] w-full rounded-lg border border-[hsl(var(--divider-subtle))] bg-[hsl(var(--input-bg))] px-4 py-3 text-sm leading-relaxed text-[hsl(var(--foreground))] transition-colors duration-150",
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
Textarea.displayName = "Textarea";