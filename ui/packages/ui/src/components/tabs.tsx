import * as TabsPrimitive from "@radix-ui/react-tabs";
import * as React from "react";
import { cn } from "../lib/utils";

export const Tabs = TabsPrimitive.Root;

export function TabsList({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      className={cn(
        "flex w-full min-w-0 flex-wrap items-center gap-1 border-b border-[hsl(var(--divider))]",
        className,
      )}
      {...props}
    />
  );
}

export function TabsTrigger({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        "relative -mb-px inline-flex h-10 cursor-pointer items-center justify-center whitespace-nowrap px-4 text-sm font-medium text-[hsl(var(--muted-foreground))] transition-colors duration-150",
        "border-b-2 border-transparent",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))] focus-visible:ring-offset-2 focus-visible:ring-offset-[hsl(var(--background))]",
        "disabled:pointer-events-none disabled:opacity-50",
        "hover:text-[hsl(var(--foreground))]",
        "data-[state=active]:border-[hsl(var(--primary))] data-[state=active]:text-[hsl(var(--primary))]",
        className,
      )}
      {...props}
    />
  );
}

export function TabsContent({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>) {
  return (
    <TabsPrimitive.Content
      className={cn("mt-6 min-w-0 focus-visible:outline-none", className)}
      {...props}
    />
  );
}