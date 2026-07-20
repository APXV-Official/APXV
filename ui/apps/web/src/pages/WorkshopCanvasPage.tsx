import {
  getPipeline,
  listPipelines,
  type PipelineDocument,
  type PipelineStep,
} from "@apxv/api-client";
import {
  Alert,
  AlertDescription,
  Button,
  EmptyState,
  PageToolbar,
  SectionHeader,
  Select,
  Skeleton,
} from "@apxv/ui";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { PageShell } from "../components/PageShell";
import { formatApiError } from "../lib/api-errors";

const NODE_W = 160;
const NODE_H = 56;

function stepPosition(step: PipelineStep, index: number) {
  const layout = step.layout as { x?: number; y?: number } | undefined;
  return {
    x: typeof layout?.x === "number" ? layout.x : 40 + (index % 4) * 200,
    y: typeof layout?.y === "number" ? layout.y : 40 + Math.floor(index / 4) * 100,
  };
}

function edgeStroke(label?: string): string {
  const k = (label || "").toLowerCase();
  if (k === "failure" || k === "fail") return "hsl(0 72% 58%)";
  if (k === "success" || k === "out" || k === "always") return "hsl(187 70% 48%)";
  if (k === "next") return "hsl(var(--muted-foreground) / 0.65)";
  return "hsl(var(--muted-foreground) / 0.8)";
}

function edgeDash(label?: string): string | undefined {
  const k = (label || "").toLowerCase();
  if (k === "failure" || k === "fail") return "5 4";
  if (k === "next") return "3 3";
  return undefined;
}

export function WorkshopCanvasPage() {
  const { id: searchId } = useSearch({ from: "/shell/workshop/canvas" });
  const navigate = useNavigate();
  const [selected, setSelected] = useState<string | undefined>(searchId);

  const listQuery = useQuery({
    queryKey: ["pipelines"],
    queryFn: () => listPipelines(),
  });

  const detailQuery = useQuery({
    queryKey: ["pipelines", "detail", selected],
    queryFn: () => getPipeline(selected!),
    enabled: Boolean(selected),
  });

  const doc: PipelineDocument | undefined = detailQuery.data?.pipeline;
  const nodes = useMemo(() => {
    if (!doc) return [];
    return doc.steps.map((step, index) => ({
      step,
      index,
      ...stepPosition(step, index),
    }));
  }, [doc]);

  const edges = useMemo(() => {
    if (!doc) return [] as Array<{ from: string; to: string; label?: string }>;
    const edgesOut: Array<{ from: string; to: string; label?: string }> = [];
    const freeform = doc.edges ?? [];
    if (freeform.length > 0) {
      for (const e of freeform) {
        if (!e.from || !e.to) continue;
        edgesOut.push({
          from: e.from,
          to: e.to,
          label: e.kind || "edge",
        });
      }
      return edgesOut;
    }
    // Linear / next_* fallback when board has no freeform edges
    doc.steps.forEach((step, index) => {
      if (step.next_on_success) {
        edgesOut.push({
          from: step.id,
          to: step.next_on_success,
          label: "success",
        });
      } else if (index + 1 < doc.steps.length) {
        edgesOut.push({
          from: step.id,
          to: doc.steps[index + 1].id,
          label: "next",
        });
      }
      if (step.next_on_failure) {
        edgesOut.push({
          from: step.id,
          to: step.next_on_failure,
          label: "failure",
        });
      }
    });
    return edgesOut;
  }, [doc]);

  const bounds = useMemo(() => {
    if (nodes.length === 0) return { w: 640, h: 420 };
    let maxX = 0;
    let maxY = 0;
    for (const n of nodes) {
      maxX = Math.max(maxX, n.x + NODE_W + 48);
      maxY = Math.max(maxY, n.y + NODE_H + 48);
    }
    return { w: Math.max(640, maxX), h: Math.max(420, maxY) };
  }, [nodes]);

  return (
    <PageShell>
      <SectionHeader title="Pipeline canvas" />
      <p className="text-sm text-[hsl(var(--muted-foreground))]">
        Visual view of the same Pipeline Spec — freeform wires when present,
        otherwise linear order. Edit on Workbench; YAML remains source of truth.
      </p>
      <PageToolbar>
        <Button variant="secondary" asChild>
          <Link to="/workshop/library">Library</Link>
        </Button>
        <Button
          variant="secondary"
          disabled={!selected}
          onClick={() =>
            void navigate({
              to: "/workshop",
              search: { id: selected, shelf: undefined },
            })
          }
        >
          Open on Workbench
        </Button>
        <Button
          variant="secondary"
          disabled={!selected}
          onClick={() =>
            void navigate({
              to: "/workshop/composer",
              search: { id: selected },
            })
          }
        >
          Open in composer
        </Button>
      </PageToolbar>

      <div className="mb-4 max-w-md">
        <Select
          value={selected ?? ""}
          onChange={(e) => {
            const id = e.target.value || undefined;
            setSelected(id);
            void navigate({
              to: "/workshop/canvas",
              search: { id },
            });
          }}
        >
          <option value="">Select a local pipeline…</option>
          {(listQuery.data?.pipelines ?? []).map((p) => (
            <option key={p.id} value={p.id}>
              {p.name || p.id}
            </option>
          ))}
        </Select>
      </div>

      {detailQuery.isError ? (
        <Alert variant="destructive">
          <AlertDescription>
            {formatApiError(detailQuery.error)}
          </AlertDescription>
        </Alert>
      ) : null}

      {!selected ? (
        <EmptyState
          title="Choose a pipeline"
          description="Canvas visualizes steps and jump edges from the stored Spec."
          action={
            <Button size="sm" asChild>
              <Link to="/workshop/library">Open library</Link>
            </Button>
          }
        />
      ) : detailQuery.isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : doc ? (
        <div
          className="relative overflow-auto rounded-lg border border-[hsl(var(--divider-subtle))] bg-[hsl(var(--surface))]"
          style={{
            minHeight: 420,
            backgroundImage:
              "radial-gradient(circle at 1px 1px, hsl(var(--divider-subtle)) 1px, transparent 0)",
            backgroundSize: "16px 16px",
          }}
        >
          <div
            className="relative"
            style={{ width: bounds.w, height: bounds.h, minHeight: 420 }}
          >
            <svg
              className="pointer-events-none absolute inset-0"
              width={bounds.w}
              height={bounds.h}
              aria-hidden
            >
              <defs>
                <marker
                  id="apxv-canvas-arrow"
                  markerWidth="8"
                  markerHeight="8"
                  refX="7"
                  refY="3"
                  orient="auto"
                >
                  <path
                    d="M0,0 L7,3 L0,6 Z"
                    fill="hsl(var(--muted-foreground))"
                  />
                </marker>
                <marker
                  id="apxv-canvas-arrow-ok"
                  markerWidth="8"
                  markerHeight="8"
                  refX="7"
                  refY="3"
                  orient="auto"
                >
                  <path d="M0,0 L7,3 L0,6 Z" fill="hsl(187 70% 48%)" />
                </marker>
                <marker
                  id="apxv-canvas-arrow-fail"
                  markerWidth="8"
                  markerHeight="8"
                  refX="7"
                  refY="3"
                  orient="auto"
                >
                  <path d="M0,0 L7,3 L0,6 Z" fill="hsl(0 72% 58%)" />
                </marker>
              </defs>
              {edges.map((e, i) => {
                const a = nodes.find((n) => n.step.id === e.from);
                const b = nodes.find((n) => n.step.id === e.to);
                if (!a || !b) return null;
                const x1 = a.x + NODE_W;
                const y1 = a.y + NODE_H / 2;
                const x2 = b.x;
                const y2 = b.y + NODE_H / 2;
                const midX = (x1 + x2) / 2;
                const stroke = edgeStroke(e.label);
                const k = (e.label || "").toLowerCase();
                const marker =
                  k === "failure" || k === "fail"
                    ? "url(#apxv-canvas-arrow-fail)"
                    : k === "success" || k === "out" || k === "always"
                      ? "url(#apxv-canvas-arrow-ok)"
                      : "url(#apxv-canvas-arrow)";
                return (
                  <g key={`${e.from}-${e.to}-${i}`}>
                    <path
                      d={`M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`}
                      fill="none"
                      stroke={stroke}
                      strokeWidth={2}
                      strokeDasharray={edgeDash(e.label)}
                      markerEnd={marker}
                    />
                    {e.label ? (
                      <text
                        x={midX}
                        y={(y1 + y2) / 2 - 6}
                        textAnchor="middle"
                        fill={stroke}
                        fontSize={10}
                        className="select-none"
                      >
                        {e.label}
                      </text>
                    ) : null}
                  </g>
                );
              })}
            </svg>
            {nodes.map(({ step, x, y, index }) => (
              <div
                key={step.id}
                className="absolute w-40 rounded-md border border-[hsl(var(--divider))] bg-[hsl(var(--surface-elevated))] p-2 shadow-sm ring-1 ring-black/5"
                style={{ left: x, top: y, width: NODE_W }}
              >
                <div className="mb-0.5 flex items-center justify-between gap-1">
                  <p className="truncate text-sm font-medium">{step.name}</p>
                  <span className="shrink-0 rounded bg-[hsl(var(--overlay-muted))] px-1 text-[9px] text-[hsl(var(--muted-foreground))]">
                    {index + 1}
                  </span>
                </div>
                <p className="truncate font-mono text-[10px] text-[hsl(var(--muted-foreground))]">
                  {step.id}
                </p>
                <p className="mt-1 truncate text-[10px] text-[hsl(var(--muted-foreground))]">
                  {step.uses}
                </p>
              </div>
            ))}
          </div>
          <div className="sticky bottom-0 flex flex-wrap gap-3 border-t border-[hsl(var(--divider-subtle))] bg-[hsl(var(--surface))]/95 px-3 py-2 text-[10px] text-[hsl(var(--muted-foreground))] backdrop-blur">
            <span className="inline-flex items-center gap-1.5">
              <span
                className="inline-block h-0.5 w-4 rounded"
                style={{ background: "hsl(187 70% 48%)" }}
              />
              success / wire
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span
                className="inline-block h-0.5 w-4 rounded"
                style={{
                  background: "hsl(0 72% 58%)",
                  backgroundImage:
                    "repeating-linear-gradient(90deg, hsl(0 72% 58%), hsl(0 72% 58%) 3px, transparent 3px, transparent 6px)",
                }}
              />
              failure
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4 rounded bg-[hsl(var(--muted-foreground)/0.65)]" />
              linear next
            </span>
            <span className="ml-auto font-mono">
              {doc.steps.length} steps · {edges.length} edges
              {(doc.edges?.length ?? 0) > 0 ? " · freeform" : " · linear"}
            </span>
          </div>
        </div>
      ) : null}
    </PageShell>
  );
}
