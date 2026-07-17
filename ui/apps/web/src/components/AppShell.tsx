import { APXV_UI_VERSION } from "@apxv/types";
import { Button } from "@apxv/ui";
import { Link, useRouterState } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import {
  Archive,
  Clock,
  LayoutDashboard,
  Bot,
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
import type { ReactNode } from "react";
import { useState } from "react";

import { defaultNavSearch } from "../lib/nav-search";
import { BrandLogo } from "./BrandLogo";
import { CommandPalette, CommandPaletteTrigger } from "./CommandPalette";
import { IntegrityBadge } from "./IntegrityBadge";

type NavItem = { to: string; label: string; icon: LucideIcon };

const NAV_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: "Overview",
    items: [{ to: "/", label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Operations",
    items: [
      { to: "/packs", label: "Agent packs", icon: Package },
      { to: "/agents", label: "Agents", icon: Bot },
      { to: "/pipeline", label: "Pipeline", icon: Play },
      { to: "/jobs", label: "Jobs", icon: Clock },
      { to: "/artifacts", label: "Artifacts", icon: Archive },
    ],
  },
  {
    label: "Trust",
    items: [
      { to: "/verify", label: "Verify", icon: ShieldCheck },
      { to: "/audit", label: "Audit", icon: ScrollText },
      { to: "/governance", label: "Governance", icon: Scale },
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
  "/": "Runtime overview and recent activity",
  "/packs": "Pack studio — wizard, install, activate, clone, and run packs",
  "/agents": "Core and pack agents, capabilities, and chains",
  "/pipeline": "Run governed pipelines with attestation",
  "/jobs": "Pipeline queue and job inspection",
  "/artifacts": "Stored outputs and attestations",
  "/verify": "Validate attestation proofs",
  "/audit": "Explore tamper-evident audit logs",
  "/governance": "Rules, workflows, and proposals",
  "/system": "Health checks, backups, and integrations",
  "/settings": "Connection and operator preferences",
};

function resolvePageMeta(pathname: string): { title: string; description: string } {
  if (pathname.startsWith("/artifacts/") && pathname !== "/artifacts") {
    return {
      title: "Artifact detail",
      description: "Inspect stored output, redactions, and proofs",
    };
  }
  return {
    title: pageTitle(pathname),
    description: pageDescription(pathname),
  };
}

function pageTitle(pathname: string): string {
  for (const group of NAV_GROUPS) {
    const item = group.items.find((n) =>
      n.to === "/"
        ? pathname === "/"
        : pathname === n.to || pathname.startsWith(`${n.to}/`),
    );
    if (item) return item.label;
  }
  return "APXV";
}

function pageDescription(pathname: string): string {
  for (const [path, description] of Object.entries(PAGE_DESCRIPTIONS)) {
    if (
      path === "/"
        ? pathname === "/"
        : pathname === path || pathname.startsWith(`${path}/`)
    ) {
      return description;
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
  ] as const;
  for (const key of keys) {
    void queryClient.invalidateQueries({ queryKey: [key] });
  }
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const queryClient = useQueryClient();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { title, description } = resolvePageMeta(pathname);

  return (
    <div className="flex min-h-screen bg-[hsl(var(--background))]">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-[hsl(var(--primary))] focus:px-4 focus:py-2 focus:text-[hsl(var(--primary-foreground))]"
      >
        Skip to main content
      </a>

      <aside
        className="flex w-[18rem] shrink-0 flex-col border-r border-[hsl(var(--divider-subtle))] bg-[hsl(var(--sidebar))]"
        aria-label="Primary navigation"
      >
        <div className="px-6 pb-8 pt-8">
          <BrandLogo size="lg" showSubtitle />
        </div>

        <nav
          className="flex flex-1 flex-col gap-7 overflow-y-auto px-5 pb-6"
          aria-label="Application"
        >
          {NAV_GROUPS.map((group) => (
            <div key={group.label}>
              <p className="mb-2.5 px-4 text-[0.6875rem] font-semibold uppercase tracking-[0.14em] text-[hsl(var(--caption))]">
                {group.label}
              </p>
              <div className="flex flex-col gap-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const active =
                    item.to === "/"
                      ? pathname === "/"
                      : pathname === item.to ||
                        pathname.startsWith(`${item.to}/`);
                  return (
                    <Link
                      key={item.to}
                      to={item.to}
                      search={defaultNavSearch(item.to)}
                      className={[
                        "relative flex cursor-pointer items-center gap-3 rounded-lg px-4 py-2.5 text-[0.9375rem] transition-colors",
                        active
                          ? "bg-[hsl(var(--overlay))] font-medium text-[hsl(var(--foreground))] before:absolute before:left-0 before:top-1/2 before:h-5 before:w-0.5 before:-translate-y-1/2 before:rounded-full before:bg-[hsl(var(--primary))]"
                          : "text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--overlay-subtle))] hover:text-[hsl(var(--foreground))]",
                      ].join(" ")}
                    >
                      <Icon className="h-[1.125rem] w-[1.125rem] shrink-0 opacity-80" aria-hidden />
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="space-y-4 px-5 pb-7">
          <IntegrityBadge />
          <div className="space-y-1 px-1 text-center">
            <p className="text-xs text-[hsl(var(--caption))]">
              APXV™ v{APXV_UI_VERSION}
            </p>
            <p className="text-[0.625rem] tracking-wide text-[hsl(var(--caption))]/70">
              Governed · Local · Verified
            </p>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 border-b border-[hsl(var(--divider-subtle))] bg-[hsl(var(--background))]/95 px-[var(--page-x)] py-5 backdrop-blur-md">
          <div className="flex items-start justify-between gap-6">
            <div className="min-w-0 space-y-1">
              <h1 className="text-xl font-semibold tracking-tight text-[hsl(var(--foreground))] sm:text-2xl">
                {title}
              </h1>
              <p className="text-sm text-[hsl(var(--muted-foreground))]">
                {description}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-5 pt-0.5">
              <CommandPaletteTrigger onClick={() => setPaletteOpen(true)} />
              <Button
                variant="ghost"
                size="sm"
                className="gap-2 text-[hsl(var(--muted-foreground))]"
                onClick={() => refreshAll(queryClient)}
                aria-label="Refresh all data from the runtime"
              >
                <RefreshCw className="h-4 w-4" aria-hidden />
                Refresh
              </Button>
            </div>
          </div>
        </header>

        <CommandPalette
          open={paletteOpen}
          onOpenChange={setPaletteOpen}
          onRefresh={() => refreshAll(queryClient)}
        />

        <main
          id="main-content"
          className="min-w-0 flex-1 overflow-auto px-[var(--page-x)] pb-[var(--page-y)] pt-6 animate-fade-in"
          tabIndex={-1}
        >
          {children}
        </main>
      </div>
    </div>
  );
}