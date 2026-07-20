import * as React from "react";
import { cn } from "../lib/utils";

export function Label({
  className,
  ...props
}: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={cn(
        "text-xs font-medium leading-none text-[hsl(var(--foreground))]",
        className,
      )}
      {...props}
    />
  );
}