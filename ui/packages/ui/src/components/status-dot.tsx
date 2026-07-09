import { cn } from "../lib/utils";

const toneClass = {
  success: "bg-[hsl(var(--success))]",
  warning: "bg-[hsl(var(--warning))]",
  destructive: "bg-[hsl(var(--destructive))]",
  muted: "bg-[hsl(var(--muted-foreground))]",
  primary: "bg-[hsl(var(--primary))]",
} as const;

export function StatusDot({
  tone = "muted",
  pulse = false,
  className,
}: {
  tone?: keyof typeof toneClass;
  pulse?: boolean;
  className?: string;
}) {
  return (
    <span className={cn("relative inline-flex h-2 w-2", className)}>
      {pulse && (
        <span
          className={cn(
            "absolute inline-flex h-full w-full animate-ping rounded-full opacity-40",
            toneClass[tone],
          )}
        />
      )}
      <span
        className={cn("relative inline-flex h-2 w-2 rounded-full", toneClass[tone])}
      />
    </span>
  );
}