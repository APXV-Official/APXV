import { APXV_UI_VERSION } from "@apxv/types";
import { Button } from "@apxv/ui";
import { Link, useRouterState } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  Clock,
  FlaskConical,
  Layers,
  PanelLeftClose,
  PanelLeftOpen,
  RefreshCw,
  Server,
  Settings,
  ShieldCheck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

const NAV_COLLAPSED_KEY = "apxv.navCollapsed";

import { defaultNavSearch } from "../lib/nav-search";
import { BrandLogo } from "./BrandLogo";
import { CommandPalette, CommandPaletteTrigger } from "./CommandPalette";
import { ConnectionBanner } from "./ConnectionBanner";
import { IntegrityBadge } from "./IntegrityBadge";

type NavItem = { to: string; label: string; icon: LucideIcon; match?: string[] };

/** Endgame IA: Studio + Workbench. */
const NAV_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: "Build",
    items: [
      { to: "/workshop", label: "Workbench", icon: Layers },
      { to: "/studio", label: "Studio", icon: FlaskConical },
    ],
  },
  {
    label: "Operate",
    items: [
      { to: "/jobs", label: "Runs", icon: Clock },
      { to: "/artifacts", label: "Artifacts", icon: Archive },
    ],
  },
  {
    label: "Trust",
    items: [
      {
        to: "/trust",
        label: "Trust",
        icon: ShieldCheck,
        match: ["/trust", "/verify", "/audit", "/governance"],
      },
    ],
  },
  {
    label: "Platform",
    items: [
      { to: "/system", label: "System", icon: Server },
      { to: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

const PAGE_DESCRIPTIONS: Record<string, string> = {
  "/workshop": "Workbench — assemble pipelines from building blocks",
  "/studio": "Studio — create Agents, Packs, and Proof Profiles; test; promote",
  "/workshop/library": "Saved pipelines and examples",
  "/workshop/composer": "Ordered-list pipeline editor (power mode)",
  "/workshop/canvas": "Graph view of the same Pipeline Spec",
  "/packs": "Pack wizard (advanced) — prefer Studio",
  "/agents": "Redirects to Workbench shelf",
  "/pipeline": "Redirects to Workbench",
  "/jobs": "Run queue, traces, and human approval",
  "/artifacts": "Stored outputs and attestations",
  "/trust": "Verify proofs, audit chain, and governance",
  "/verify": "Validate attestation proofs",
  "/audit": "Explore tamper-evident audit logs",
  "/governance": "Rules, workflows, and proposals",
  "/system": "Health, doctor, backups, and integrations",
  "/settings": "Connection and operator preferences",
};

function isNavActive(pathname: string, item: NavItem): boolean {
  const paths = item.match ?? [item.to];
  return paths.some((p) =>
    p === "/workshop"
      ? pathname === "/workshop" || pathname.startsWith("/workshop/")
      : pathname === p || pathname.startsWith(`${p}/`),
  );
}

/** Exact path → shell title (when not covered by primary nav labels). */
const PAGE_TITLES: Record<string, string> = {
  "/": "Workbench",
  "/workshop": "Workbench",
  "/workshop/library": "Pipeline library",
  "/workshop/composer": "List composer",
  "/workshop/canvas": "Canvas",
  "/studio": "Studio",
  "/jobs": "Runs",
  "/artifacts": "Artifacts",
  "/trust": "Trust",
  "/verify": "Verify",
  "/audit": "Audit",
  "/governance": "Governance",
  "/system": "System",
  "/settings": "Settings",
  "/packs": "Studio (advanced packs)",
};

function resolvePageMeta(pathname: string): { title: string; description: string } {
  if (pathname.startsWith("/artifacts/") && pathname !== "/artifacts") {
    return {
      title: "Artifact detail",
      description: "Inspect stored output, redactions, and proofs",
    };
  }
  // Exact titles first so /workshop/library is not labeled "Workbench"
  if (PAGE_TITLES[pathname]) {
    return {
      title: PAGE_TITLES[pathname],
      description: pageDescription(pathname),
    };
  }
  for (const group of NAV_GROUPS) {
    for (const item of group.items) {
      if (isNavActive(pathname, item)) {
        return {
          title: item.label,
          description:
            PAGE_DESCRIPTIONS[item.to] ??
            pageDescription(pathname) ??
            "Governed local agent operations",
        };
      }
    }
  }
  return {
    title: pageTitleFallback(pathname),
    description: pageDescription(pathname),
  };
}

function pageTitleFallback(pathname: string): string {
  if (pathname.startsWith("/workshop")) return "Workbench";
  if (pathname === "/jobs") return "Runs";
  if (pathname === "/verify") return "Verify";
  if (pathname === "/audit") return "Audit";
  if (pathname === "/governance") return "Governance";
  if (pathname === "/packs") return "Studio (advanced packs)";
  if (pathname === "/agents") return "Agents";
  if (pathname === "/pipeline") return "Pipeline";
  return "APXV";
}

function pageDescription(pathname: string): string {
  const paths = Object.keys(PAGE_DESCRIPTIONS).sort((a, b) => b.length - a.length);
  for (const path of paths) {
    if (pathname === path || pathname.startsWith(`${path}/`)) {
      return PAGE_DESCRIPTIONS[path];
    }
  }
  return "Governed local agent operations";
}

function refreshAll(queryClient: ReturnType<typeof useQueryClient>) {
  const keys = [
    "health",
    "jobs",
    "artifacts",
    "audit",
    "backups",
    "system",
    "governance",
    "keys",
    "capabilities",
    "packs",
    "agents",
    "ollama",
    "pipelines",
    "studio",
  ] as const;
  for (const key of keys) {
    void queryClient.invalidateQueries({ queryKey: [key] });
  }
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const queryClient = useQueryClient();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [navCollapsed, setNavCollapsed] = useState(() => {
    try {
      return localStorage.getItem(NAV_COLLAPSED_KEY) === "1";
    } catch {
      return false;
    }
  });
  const { title, description } = resolvePageMeta(pathname);
  // Full-bleed board only — library/composer/canvas use the normal page chrome
  const isWorkshop = pathname === "/workshop";

  useEffect(() => {
    try {
      localStorage.setItem(NAV_COLLAPSED_KEY, navCollapsed ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [navCollapsed]);

  // Global ⌘/Ctrl+K — works on Workbench too (trigger is not mounted there)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="flex h-dvh max-h-dvh overflow-hidden bg-[hsl(var(--background))]">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-[hsl(var(--primary))] focus:px-4 focus:py-2 focus:text-[hsl(var(--primary-foreground))]"
      >
        Skip to main content
      </a>

      <aside
        className={[
          "flex shrink-0 flex-col border-r border-[hsl(var(--divider-subtle))] bg-[hsl(var(--sidebar))] transition-[width] duration-200 ease-out",
          navCollapsed ? "w-14" : "w-52",
        ].join(" ")}
        aria-label="Primary navigation"
        data-collapsed={navCollapsed ? "true" : "false"}
      >
        <div
          className={
            navCollapsed ? "flex justify-center px-1 pb-3 pt-4" : "px-3.5 pb-4 pt-5"
          }
        >
          {navCollapsed ? (
            <BrandLogo size="sm" showSubtitle={false} />
          ) : (
            <BrandLogo size="md" showSubtitle />
          )}
        </div>

        <nav
          className={[
            "flex flex-1 flex-col gap-4 overflow-y-auto pb-3",
            navCollapsed ? "px-1.5" : "px-2.5",
          ].join(" ")}
          aria-label="Application"
        >
          {NAV_GROUPS.map((group) => (
            <div key={group.label}>
              {!navCollapsed ? (
                <p className="mb-1.5 px-2.5 text-[0.625rem] font-semibold uppercase tracking-[0.12em] text-[hsl(var(--caption))]">
                  {group.label}
                </p>
              ) : (
                <div
                  className="mx-auto mb-1.5 h-px w-5 bg-[hsl(var(--divider-subtle))]"
                  aria-hidden
                />
              )}
              <div className="flex flex-col gap-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const active = isNavActive(pathname, item);
                  return (
                    <Link
                      key={item.to}
                      to={item.to}
                      search={defaultNavSearch(item.to)}
                      title={item.label}
                      aria-label={item.label}
                      className={[
                        "relative flex cursor-pointer items-center rounded-md py-2 text-[0.8125rem] transition-colors",
                        navCollapsed
                          ? "justify-center px-2"
                          : "gap-2.5 px-2.5",
                        active
                          ? "bg-[hsl(var(--overlay))] font-medium text-[hsl(var(--foreground))] before:absolute before:left-0 before:top-1/2 before:h-4 before:w-0.5 before:-translate-y-1/2 before:rounded-full before:bg-[hsl(var(--primary))]"
                          : "text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--overlay-subtle))] hover:text-[hsl(var(--foreground))]",
                      ].join(" ")}
                    >
                      <Icon
                        className="h-4 w-4 shrink-0 opacity-80"
                        aria-hidden
                      />
                      {!navCollapsed ? item.label : null}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div
          className={[
            "space-y-2 border-t border-[hsl(var(--divider-subtle))] pb-4 pt-3",
            navCollapsed ? "px-1.5" : "px-4",
          ].join(" ")}
        >
          {!navCollapsed ? <IntegrityBadge /> : null}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className={[
              "w-full gap-2 text-[hsl(var(--muted-foreground))]",
              navCollapsed ? "justify-center px-0" : "justify-start",
            ].join(" ")}
            onClick={() => setNavCollapsed((c) => !c)}
            aria-label={navCollapsed ? "Expand navigation" : "Collapse navigation"}
            title={navCollapsed ? "Expand navigation" : "Collapse navigation"}
          >
            {navCollapsed ? (
              <PanelLeftOpen className="h-4 w-4" aria-hidden />
            ) : (
              <>
                <PanelLeftClose className="h-4 w-4" aria-hidden />
                Collapse
              </>
            )}
          </Button>
          {!navCollapsed ? (
            <div className="space-y-1 px-1 text-center">
              <p className="text-xs text-[hsl(var(--caption))]">
                APXV™ v{APXV_UI_VERSION}
              </p>
              <p className="text-[0.625rem] tracking-wide text-[hsl(var(--caption))]/70">
                APXV · Local · Verified
              </p>
            </div>
          ) : null}
        </div>
      </aside>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        {!isWorkshop ? (
          <header className="sticky top-0 z-10 shrink-0 border-b border-[hsl(var(--divider-subtle))] bg-[hsl(var(--background))]/95 px-[var(--page-x)] py-3.5 backdrop-blur-md">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 space-y-0.5">
                <h1 className="text-lg font-semibold tracking-tight text-[hsl(var(--foreground))]">
                  {title}
                </h1>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  {description}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-3 pt-0.5">
                <CommandPaletteTrigger onClick={() => setPaletteOpen(true)} />
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1.5 text-xs text-[hsl(var(--muted-foreground))]"
                  onClick={() => refreshAll(queryClient)}
                  aria-label="Refresh all data from the runtime"
                >
                  <RefreshCw className="h-3.5 w-3.5" aria-hidden />
                  Refresh
                </Button>
              </div>
            </div>
          </header>
        ) : null}

        <CommandPalette
          open={paletteOpen}
          onOpenChange={setPaletteOpen}
          onRefresh={() => refreshAll(queryClient)}
        />

        <main
          id="main-content"
          className={
            isWorkshop
              ? "flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden p-0 animate-fade-in"
              : "min-h-0 min-w-0 flex-1 overflow-auto px-[var(--page-x)] pb-[var(--page-y)] pt-4 animate-fade-in"
          }
          tabIndex={-1}
        >
          {/* Health/connection banner on all pages including Workbench */}
          {isWorkshop ? (
            <div className="shrink-0 border-b border-white/10 bg-[#0c0f14] px-3 py-1.5">
              <ConnectionBanner />
            </div>
          ) : null}
          {children}
        </main>
      </div>
    </div>
  );
}
