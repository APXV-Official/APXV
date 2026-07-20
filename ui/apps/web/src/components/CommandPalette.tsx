import { Button } from "@apxv/ui";
import { useNavigate } from "@tanstack/react-router";
import {
  Archive,
  Clock,
  FlaskConical,
  Layers,
  Package,
  RefreshCw,
  Scale,
  ScrollText,
  Server,
  Settings,
  ShieldCheck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type CommandItem = {
  id: string;
  label: string;
  group: string;
  icon: LucideIcon;
  keywords?: string;
  action: () => void;
};

export function CommandPalette({
  open,
  onOpenChange,
  onRefresh,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRefresh: () => void;
}) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const close = useCallback(() => {
    onOpenChange(false);
    setQuery("");
  }, [onOpenChange]);

  const go = useCallback(
    (to: string, search?: Record<string, unknown>) => {
      close();
      void navigate({ to, search });
    },
    [close, navigate],
  );

  const commands = useMemo<CommandItem[]>(
    () => [
      {
        id: "nav-workshop",
        label: "Workbench",
        group: "Navigate",
        icon: Layers,
        keywords: "home board compose building blocks pipeline workshop",
        action: () => go("/workshop", { id: undefined, shelf: undefined }),
      },
      {
        id: "nav-studio",
        label: "Studio",
        group: "Navigate",
        icon: FlaskConical,
        keywords: "create agent pack promote test proof",
        action: () => go("/studio", { tab: undefined }),
      },
      {
        id: "nav-runs",
        label: "Runs",
        group: "Navigate",
        icon: Clock,
        keywords: "jobs queue trace",
        action: () => go("/jobs", { id: undefined }),
      },
      {
        id: "nav-artifacts",
        label: "Artifacts",
        group: "Navigate",
        icon: Archive,
        action: () => go("/artifacts"),
      },
      {
        id: "nav-trust",
        label: "Trust",
        group: "Navigate",
        icon: ShieldCheck,
        keywords: "verify audit governance",
        action: () => go("/trust"),
      },
      {
        id: "nav-verify",
        label: "Verify",
        group: "Trust",
        icon: ShieldCheck,
        action: () => go("/verify", { hash: undefined, job: undefined }),
      },
      {
        id: "nav-audit",
        label: "Audit",
        group: "Trust",
        icon: ScrollText,
        action: () => go("/audit"),
      },
      {
        id: "nav-governance",
        label: "Governance",
        group: "Trust",
        icon: Scale,
        action: () => go("/governance", { tab: undefined, proposal: undefined }),
      },
      {
        id: "nav-system",
        label: "System",
        group: "Navigate",
        icon: Server,
        keywords: "health doctor backups sovereign keys",
        action: () => go("/system", { tab: "health" }),
      },
      {
        id: "nav-settings",
        label: "Settings",
        group: "Navigate",
        icon: Settings,
        action: () => go("/settings"),
      },
      {
        id: "nav-library",
        label: "Pipeline library",
        group: "Workbench",
        icon: Layers,
        keywords: "templates saved pipelines examples",
        action: () => go("/workshop/library"),
      },
      {
        id: "pack-wizard",
        label: "Advanced pack wizard",
        group: "Author",
        icon: Package,
        keywords: "wizard pack authoring advanced studio",
        action: () => go("/packs", { wizard: "1", pack: undefined }),
      },
      {
        id: "refresh",
        label: "Refresh data",
        group: "Actions",
        icon: RefreshCw,
        action: () => {
          onRefresh();
          close();
        },
      },
    ],
    [close, go, onRefresh],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter(
      (c) =>
        c.label.toLowerCase().includes(q) ||
        c.group.toLowerCase().includes(q) ||
        (c.keywords ?? "").includes(q),
    );
  }, [commands, query]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query, open]);

  useEffect(() => {
    if (!open) return;
    const t = window.setTimeout(() => inputRef.current?.focus(), 10);
    return () => window.clearTimeout(t);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => Math.min(i + 1, Math.max(filtered.length - 1, 0)));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter" && filtered[activeIndex]) {
        e.preventDefault();
        filtered[activeIndex].action();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, close, filtered, activeIndex]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 px-4 pt-[12vh]"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div className="w-full max-w-lg overflow-hidden rounded-xl border border-[hsl(var(--divider-subtle))] bg-[hsl(var(--surface))] shadow-2xl">
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Go to Workbench, Studio, Runs, Trust…"
          className="w-full border-b border-[hsl(var(--divider-subtle))] bg-transparent px-4 py-3 text-sm outline-none"
          aria-label="Filter commands"
        />
        <ul className="max-h-80 overflow-y-auto p-2" role="listbox">
          {filtered.length === 0 ? (
            <li className="px-3 py-6 text-center text-sm text-[hsl(var(--muted-foreground))]">
              No matches
            </li>
          ) : (
            filtered.map((item, index) => {
              const Icon = item.icon;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={index === activeIndex}
                    className={[
                      "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm",
                      index === activeIndex
                        ? "bg-[hsl(var(--overlay))]"
                        : "hover:bg-[hsl(var(--overlay-subtle))]",
                    ].join(" ")}
                    onMouseEnter={() => setActiveIndex(index)}
                    onClick={() => item.action()}
                  >
                    <Icon className="h-4 w-4 shrink-0 opacity-70" />
                    <span className="flex-1">{item.label}</span>
                    <span className="text-xs text-[hsl(var(--muted-foreground))]">
                      {item.group}
                    </span>
                  </button>
                </li>
              );
            })
          )}
        </ul>
        <div className="flex justify-end border-t border-[hsl(var(--divider-subtle))] px-3 py-2">
          <Button size="sm" variant="ghost" onClick={close}>
            Esc
          </Button>
        </div>
      </div>
    </div>
  );
}

export function CommandPaletteTrigger({ onClick }: { onClick: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onClick();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClick]);

  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={onClick}
      className="gap-2 text-[hsl(var(--muted-foreground))]"
      aria-label="Open command palette"
    >
      <span className="hidden sm:inline">Commands</span>
      <kbd className="rounded border border-[hsl(var(--divider-subtle))] px-1.5 py-0.5 font-mono text-[10px]">
        {typeof navigator !== "undefined" &&
        /Mac|iPhone|iPad/.test(navigator.platform)
          ? "⌘K"
          : "Ctrl+K"}
      </kbd>
    </Button>
  );
}
