import { cn } from "@apxv/ui";
import { isTauri } from "../lib/tauri";

export function BrandLogo({
  size = "md",
  showSubtitle = true,
  className,
}: {
  size?: "sm" | "md" | "lg";
  showSubtitle?: boolean;
  className?: string;
}) {
  const textSize =
    size === "lg" ? "text-2xl" : size === "sm" ? "text-base" : "text-lg";

  return (
    <div className={cn("min-w-0", className)}>
      <div className={cn("leading-none", textSize)}>
        <span className="font-bold tracking-tight text-white">APXV</span>
      </div>
      {showSubtitle && !isTauri() && (
        <p className="mt-1.5 text-sm font-medium tracking-wide text-[hsl(var(--muted-foreground))]">
          Sovereign operator console
        </p>
      )}
    </div>
  );
}