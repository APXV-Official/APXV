import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "../lib/utils";

const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium",
    "cursor-pointer border-0 bg-transparent shadow-none",
    "transition-[color,background-color] duration-150",
    "hover:bg-[hsl(var(--overlay-subtle))]",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))] focus-visible:ring-offset-0",
    "disabled:cursor-not-allowed disabled:pointer-events-none disabled:opacity-50 disabled:hover:bg-transparent",
  ].join(" "),
  {
    variants: {
      variant: {
        default: [
          "font-semibold text-[hsl(var(--primary))]",
          "hover:text-[hsl(var(--primary-hover))] hover:underline",
        ].join(" "),
        secondary: [
          "text-[hsl(var(--foreground))]",
          "hover:text-[hsl(var(--primary))] hover:underline",
        ].join(" "),
        outline: [
          "text-[hsl(var(--foreground))]",
          "hover:text-[hsl(var(--primary))] hover:underline",
        ].join(" "),
        ghost: [
          "text-[hsl(var(--muted-foreground))]",
          "hover:text-[hsl(var(--foreground))]",
        ].join(" "),
        link: [
          "text-[hsl(var(--primary))]",
          "hover:text-[hsl(var(--primary-hover))] hover:underline",
        ].join(" "),
        destructive: [
          "text-[hsl(var(--destructive))]",
          "hover:brightness-110 hover:underline",
        ].join(" "),
      },
      size: {
        default: "min-h-9 px-3.5 py-2",
        sm: "min-h-8 px-3 py-1.5 text-[0.8125rem]",
        lg: "min-h-10 px-4 py-2.5 text-base",
        icon: "min-h-9 min-w-9 p-2",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";