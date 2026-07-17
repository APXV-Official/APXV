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
  const markSize =
    size === "lg" ? "h-10 w-10" : size === "sm" ? "h-7 w-7" : "h-8 w-8";

  return (
    <div className={cn("flex min-w-0 items-center gap-2.5", className)}>
      <img
        src="/apxv-logo.svg"
        alt=""
        aria-hidden
        className={cn(markSize, "shrink-0 rounded-lg")}
      />
      <div className="min-w-0">
        <div className={cn("leading-none", textSize)}>
          <span className="font-bold tracking-tight text-white">APXV™</span>
        </div>
        {showSubtitle && !isTauri() && (
          <p className="mt-1.5 text-sm font-medium tracking-wide text-[hsl(var(--muted-foreground))]">
            Sovereign operator console
          </p>
        )}
      </div>
    </div>
  );
}