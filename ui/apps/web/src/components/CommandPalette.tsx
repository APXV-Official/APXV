import { Button } from "@apxv/ui";
import { useNavigate } from "@tanstack/react-router";
import {
  Archive,
  Bot,
  Clock,
  LayoutDashboard,
  Package,
  Play,
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
        id: "nav-dashboard",
        label: "Dashboard",
        group: "Navigate",
        icon: LayoutDashboard,
        action: () => go("/"),
      },
      {
        id: "nav-packs",
        label: "Agent packs",
        group: "Navigate",
        icon: Package,
        keywords: "pack studio",
        action: () => go("/packs"),
      },
      {
        id: "nav-agents",
        label: "Agents",
        group: "Navigate",
        icon: Bot,
        keywords: "registry agent",
        action: () => go("/agents"),
      },
      {
        id: "nav-pipeline",
        label: "Pipeline",
        group: "Navigate",
        icon: Play,
        action: () => go("/pipeline"),
      },
      {
        id: "nav-jobs",
        label: "Jobs",
        group: "Navigate",
        icon: Clock,
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
        id: "nav-verify",
        label: "Verify",
        group: "Navigate",
        icon: ShieldCheck,
        action: () => go("/verify", { hash: undefined }),
      },
      {
        id: "nav-audit",
        label: "Audit",
        group: "Navigate",
        icon: ScrollText,
        action: () => go("/audit"),
      },
      {
        id: "nav-governance",
        label: "Governance",
        group: "Navigate",
        icon: Scale,
        action: () => go("/governance", { tab: undefined, proposal: undefined }),
      },
      {
        id: "nav-system",
        label: "System",
        group: "Navigate",
        icon: Server,
        action: () => go("/system", { tab: undefined }),
      },
      {
        id: "nav-settings",
        label: "Settings",
        group: "Navigate",
        icon: Settings,
        action: () => go("/settings"),
      },
      {
        id: "action-refresh",
        label: "Refresh all data",
        group: "Actions",
        icon: RefreshCw,
        keywords: "reload sync",
        action: () => {
          close();
          onRefresh();
        },
      },
    ],
    [close, go, onRefresh],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter(
      (cmd) =>
        cmd.label.toLowerCase().includes(q) ||
        cmd.group.toLowerCase().includes(q) ||
        cmd.keywords?.toLowerCase().includes(q),
    );
  }, [commands, query]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  useEffect(() => {
    if (!open) return;
    const t = window.setTimeout(() => inputRef.current?.focus(), 0);
    return () => window.clearTimeout(t);
  }, [open]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onOpenChange(!open);
        return;
      }
      if (!open) return;
      if (e.key === "Escape") {
        e.preventDefault();
        close();
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => Math.min(i + 1, Math.max(filtered.length - 1, 0)));
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
      }
      if (e.key === "Enter" && filtered[activeIndex]) {
        e.preventDefault();
        filtered[activeIndex].action();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onOpenChange, close, filtered, activeIndex]);

  if (!open) return null;

  const groups = [...new Set(filtered.map((c) => c.group))];

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 px-4 pt-[min(18vh,10rem)] backdrop-blur-sm"
      role="presentation"
      onClick={close}
    >
      <div
        role="dialog"
        aria-label="Command palette"
        className="w-full max-w-lg overflow-hidden rounded-xl border border-[hsl(var(--divider-subtle))] bg-[hsl(var(--surface-elevated))] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-[hsl(var(--divider))] px-5 py-4">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search pages and actions…"
            className="w-full bg-transparent text-base text-[hsl(var(--foreground))] outline-none placeholder:text-[hsl(var(--muted-foreground))]"
            aria-label="Search commands"
          />
        </div>
        <ul className="max-h-80 overflow-y-auto py-2" role="listbox">
          {filtered.length === 0 ? (
            <li className="px-5 py-8 text-center text-sm text-[hsl(var(--muted-foreground))]">
              No matching commands
            </li>
          ) : (
            groups.map((group) => (
              <li key={group}>
                <p className="px-5 pb-1.5 pt-3 text-xs font-semibold uppercase tracking-wider text-[hsl(var(--caption))]">
                  {group}
                </p>
                <ul>
                  {filtered
                    .filter((cmd) => cmd.group === group)
                    .map((cmd) => {
                      const globalIndex = filtered.indexOf(cmd);
                      const Icon = cmd.icon;
                      const active = globalIndex === activeIndex;
                      return (
                        <li key={cmd.id}>
                          <button
                            type="button"
                            role="option"
                            aria-selected={active}
                            className={[
                              "flex w-full cursor-pointer items-center gap-3 px-5 py-3 text-left text-sm transition-colors",
                              active
                                ? "bg-[hsl(var(--primary-muted)/0.1)] text-[hsl(var(--foreground))]"
                                : "text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--overlay))]",
                            ].join(" ")}
                            onMouseEnter={() => setActiveIndex(globalIndex)}
                            onClick={() => cmd.action()}
                          >
                            <Icon className="h-4 w-4 shrink-0" aria-hidden />
                            <span>{cmd.label}</span>
                          </button>
                        </li>
                      );
                    })}
                </ul>
              </li>
            ))
          )}
        </ul>
        <div className="flex items-center justify-between border-t border-[hsl(var(--divider))] px-5 py-3 text-xs text-[hsl(var(--caption))]">
          <span>↑↓ navigate · Enter select · Esc close</span>
          <span className="rounded-md bg-[hsl(var(--overlay-muted))] px-1.5 py-0.5">Ctrl K</span>
        </div>
      </div>
    </div>
  );
}

export function CommandPaletteTrigger({
  onClick,
}: {
  onClick: () => void;
}) {
  return (
    <Button
      variant="ghost"
      size="sm"
      className="hidden gap-2 text-[hsl(var(--muted-foreground))] sm:inline-flex"
      onClick={onClick}
      aria-label="Open command palette"
    >
      <span>Search</span>
      <kbd className="rounded-md bg-[hsl(var(--overlay-muted))] px-1.5 py-0.5 font-sans text-xs">
        Ctrl K
      </kbd>
    </Button>
  );
}