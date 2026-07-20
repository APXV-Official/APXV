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
    size === "lg" ? "text-lg" : size === "sm" ? "text-sm" : "text-base";
  const markSize =
    size === "lg" ? "h-8 w-8" : size === "sm" ? "h-6 w-6" : "h-7 w-7";

  return (
    <div className={cn("flex min-w-0 items-center gap-2", className)}>
      <img
        src="/apxv-logo.svg"
        alt=""
        aria-hidden
        className={cn(markSize, "shrink-0 rounded-md")}
      />
      <div className="min-w-0">
        <div className={cn("leading-none", textSize)}>
          <span className="font-bold tracking-tight text-white">APXV™</span>
        </div>
        {showSubtitle && !isTauri() && (
          <p className="mt-1 text-[11px] font-medium tracking-wide text-[hsl(var(--muted-foreground))]">
            Local operator console
          </p>
        )}
      </div>
    </div>
  );
}