import { computeLineDiff } from "../lib/diff";

const KIND_STYLES = {
  same: "text-[hsl(var(--muted-foreground))]",
  add: "bg-emerald-950/40 text-emerald-300",
  remove: "bg-red-950/40 text-red-300",
  change: "bg-amber-950/40 text-amber-200",
} as const;

export function LineDiffView({
  before,
  after,
}: {
  before: string;
  after: string;
}) {
  const diff = computeLineDiff(before, after);
  const changes = diff.filter((d) => d.kind !== "same").length;

  return (
    <div className="space-y-2">
      <p className="text-xs text-[hsl(var(--muted-foreground))]">
        {changes} changed line{changes === 1 ? "" : "s"} (current → proposed)
      </p>
      <div className="max-h-96 overflow-auto rounded-md border border-[hsl(var(--border))] font-mono text-xs">
        {diff.map((line, i) => (
          <div
            key={i}
            className={[
              "grid grid-cols-[3rem_1fr_1fr] gap-2 border-b border-[hsl(var(--border))]/50 px-2 py-0.5",
              KIND_STYLES[line.kind],
            ].join(" ")}
          >
            <span className="text-right opacity-60">
              {line.oldNum ?? ""}
              {line.oldNum && line.newNum ? "/" : ""}
              {line.newNum ?? ""}
            </span>
            <span className="truncate">{line.oldLine ?? ""}</span>
            <span className="truncate">{line.newLine ?? ""}</span>
          </div>
        ))}
      </div>
    </div>
  );
}