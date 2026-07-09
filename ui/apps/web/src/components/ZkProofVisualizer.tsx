import { Badge } from "@apxv/ui";
import { formatDisplayValue } from "../lib/format-value";
import type { ZkProofNode } from "../lib/zk-utils";

const KIND_LABELS: Record<ZkProofNode["kind"], string> = {
  governance: "Governance",
  entity: "Entity",
  artifact: "Embedded",
};

export function ZkProofVisualizer({ nodes }: { nodes: ZkProofNode[] }) {
  if (nodes.length === 0) {
    return (
      <p className="text-sm text-[hsl(var(--muted-foreground))]">
        No ZK proof data available.
      </p>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {nodes.map((node) => (
        <div
          key={node.id}
          className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-4"
        >
          <div className="mb-2 flex items-start justify-between gap-2">
            <div>
              <p className="font-mono text-sm font-medium">
                {node.circuit ?? node.id}
              </p>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                {KIND_LABELS[node.kind]} circuit
              </p>
            </div>
            {node.valid !== undefined && (
              <Badge variant={node.valid ? "success" : "destructive"}>
                {node.valid ? "VALID" : "INVALID"}
              </Badge>
            )}
          </div>

          {node.status && (
            <p className="mb-2 text-xs text-[hsl(var(--muted-foreground))]">
              Status: {node.status}
            </p>
          )}

          {node.publicInputs && Object.keys(node.publicInputs).length > 0 && (
            <div className="mt-2 rounded-md bg-[hsl(var(--muted))] p-2">
              <p className="mb-1 text-xs font-medium">Public inputs</p>
              <dl className="space-y-1">
                {Object.entries(node.publicInputs)
                  .slice(0, 6)
                  .map(([key, value]) => (
                    <div key={key} className="flex gap-2 text-xs">
                      <dt className="shrink-0 font-mono text-[hsl(var(--muted-foreground))]">
                        {key}
                      </dt>
                      <dd className="truncate font-mono">
                        {typeof value === "string"
                          ? value.length > 32
                            ? `${value.slice(0, 32)}…`
                            : value
                          : JSON.stringify(value)}
                      </dd>
                    </div>
                  ))}
              </dl>
              {Object.keys(node.publicInputs).length > 6 && (
                <p className="mt-1 text-xs text-[hsl(var(--muted-foreground))]">
                  +{Object.keys(node.publicInputs).length - 6} more fields
                </p>
              )}
            </div>
          )}

          {node.detail != null && node.detail !== "" && (
            <p className="mt-2 line-clamp-3 whitespace-pre-wrap font-mono text-xs text-[hsl(var(--muted-foreground))]">
              {formatDisplayValue(node.detail)}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}