import { useVirtualizer } from "@tanstack/react-virtual";
import { useRef, type ReactNode } from "react";
import { cn } from "@apxv/ui";

export interface VirtualColumn<T> {
  id: string;
  header: ReactNode;
  cell: (row: T) => ReactNode;
  className?: string;
  /** e.g. "8rem", "1fr", "minmax(0,2fr)" */
  width?: string;
  /** Set false for action buttons and other non-text cells */
  truncate?: boolean;
}

export function VirtualizedTable<T>({
  rows,
  columns,
  rowKey,
  estimateSize = 52,
  maxHeight = 480,
}: {
  rows: T[];
  columns: VirtualColumn<T>[];
  rowKey: (row: T) => string;
  estimateSize?: number;
  maxHeight?: number;
}) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateSize,
    overscan: 10,
  });

  if (rows.length === 0) {
    return null;
  }

  const gridTemplateColumns =
    columns
      .map((col) => col.width ?? "minmax(0, 1fr)")
      .join(" ") || `repeat(${columns.length}, minmax(0, 1fr))`;

  const virtualRows = virtualizer.getVirtualItems();

  return (
    <div
      ref={parentRef}
      className="overflow-auto rounded-xl border border-[hsl(var(--divider-subtle))] bg-[hsl(var(--surface))]"
      style={{ maxHeight }}
      role="region"
      aria-label="Scrollable table"
      tabIndex={0}
    >
      <div
        className="sticky top-0 z-10 grid border-b border-[hsl(var(--divider))] bg-[hsl(var(--surface-elevated))] text-xs font-semibold tracking-wide text-[hsl(var(--caption))]"
        style={{ gridTemplateColumns }}
        role="row"
      >
        {columns.map((col) => (
          <div
            key={col.id}
            role="columnheader"
            className={cn("min-w-0 px-4 py-3 text-left", col.className)}
          >
            {col.header}
          </div>
        ))}
      </div>

      <div
        className="relative w-full"
        style={{ height: `${virtualizer.getTotalSize()}px` }}
      >
        {virtualRows.map((virtualRow) => {
          const row = rows[virtualRow.index];
          return (
            <div
              key={rowKey(row)}
              role="row"
              className="absolute left-0 grid w-full border-b border-[hsl(var(--divider-subtle))] text-sm transition-colors hover:bg-[hsl(var(--overlay-subtle))]"
              style={{
                gridTemplateColumns,
                height: `${virtualRow.size}px`,
                transform: `translateY(${virtualRow.start}px)`,
              }}
            >
              {columns.map((col) => (
                <div
                  key={col.id}
                  role="cell"
                  className={cn(
                    "flex min-w-0 items-center px-4 py-3",
                    col.className,
                  )}
                >
                  {col.truncate === false ? (
                    col.cell(row)
                  ) : (
                    <span className="min-w-0 truncate">{col.cell(row)}</span>
                  )}
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}