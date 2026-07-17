import {
  createRootRouteWithContext,
  createRoute,
  createRouter,
  Navigate,
  Outlet,
  redirect,
} from "@tanstack/react-router";
import { AppShell } from "./components/AppShell";
import { useApp } from "./context/AppContext";
import { ArtifactDetailPage } from "./pages/ArtifactDetailPage";
import { ArtifactsPage } from "./pages/ArtifactsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { JobsPage } from "./pages/JobsPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { BootstrapPage } from "./pages/BootstrapPage";
import { SetupPage } from "./pages/SetupPage";
import { getFirstRunPath, isTauri, usesSetupFlow } from "./lib/tauri";
import { AuditPage } from "./pages/AuditPage";
import { AgentsPage } from "./pages/AgentsPage";
import { PacksPage } from "./pages/PacksPage";
import { PipelinePage } from "./pages/PipelinePage";
import { SettingsPage } from "./pages/SettingsPage";
import { SystemPage } from "./pages/SystemPage";
import { GovernancePage } from "./pages/GovernancePage";
import { VerifyPage } from "./pages/VerifyPage";
import { readOnboardedSync } from "./lib/auth-storage";
import {
  parseOnboardingRedirect,
  shellRedirectTarget,
} from "./lib/onboarding-nav";
import { normalizeSearchString, parseWizardSearch } from "./lib/route-search";
import { Skeleton } from "@apxv/ui";
import { BrandLogo } from "./components/BrandLogo";

export interface RouterContext {
  onboarded: boolean;
  sovereignReady: boolean;
}

function RootLayout() {
  const { ready } = useApp();

  if (!ready) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-[hsl(var(--background))] px-6">
        <BrandLogo size="lg" showSubtitle />
        <div className="w-full max-w-xs space-y-2">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-4/5" />
        </div>
      </div>
    );
  }

  return <Outlet />;
}

function ShellLayout() {
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}

const rootRoute = createRootRouteWithContext<RouterContext>()({
  component: RootLayout,
});

function OnboardingGate() {
  return usesSetupFlow() ? <SetupPage /> : <OnboardingPage />;
}

const bootstrapRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/bootstrap",
  component: BootstrapPage,
  validateSearch: (search: Record<string, unknown>) => ({
    redirect: typeof search.redirect === "string" ? search.redirect : undefined,
  }),
  beforeLoad: ({ context, search }) => {
    if (!isTauri()) {
      throw redirect({ to: "/onboarding", search: { redirect: search.redirect } });
    }
    if (context.sovereignReady) {
      throw redirect({ to: "/setup", search: { redirect: search.redirect } });
    }
    if (context.onboarded) {
      const target = parseOnboardingRedirect(search.redirect);
      throw redirect({ to: target.to, search: target.search });
    }
  },
});

const setupRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/setup",
  component: SetupPage,
  validateSearch: (search: Record<string, unknown>) => ({
    redirect: typeof search.redirect === "string" ? search.redirect : undefined,
  }),
  beforeLoad: ({ context, search }) => {
    if (isTauri() && !context.sovereignReady) {
      throw redirect({ to: "/bootstrap", search: { redirect: search.redirect } });
    }
    if (context.onboarded) {
      const target = parseOnboardingRedirect(search.redirect);
      throw redirect({ to: target.to, search: target.search });
    }
  },
});

const onboardingRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/onboarding",
  component: OnboardingGate,
  validateSearch: (search: Record<string, unknown>) => ({
    redirect: typeof search.redirect === "string" ? search.redirect : undefined,
  }),
  beforeLoad: ({ context, search }) => {
    if (isTauri() && !context.sovereignReady) {
      throw redirect({
        to: "/bootstrap",
        search: { redirect: search.redirect },
      });
    }
    if (usesSetupFlow()) {
      throw redirect({
        to: "/setup",
        search: { redirect: search.redirect },
      });
    }
    if (context.onboarded) {
      const target = parseOnboardingRedirect(search.redirect);
      throw redirect({ to: target.to, search: target.search });
    }
  },
});

const shellRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "shell",
  component: ShellLayout,
  beforeLoad: ({ context, location }) => {
    const redirectTarget = shellRedirectTarget(
      location.pathname,
      location.search as Record<string, unknown>,
    );
    if (isTauri() && !context.sovereignReady) {
      throw redirect({
        to: "/bootstrap",
        search: { redirect: redirectTarget },
      });
    }
    if (!context.onboarded) {
      throw redirect({
        to: getFirstRunPath(),
        search: { redirect: redirectTarget },
      });
    }
  },
});

const dashboardRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: "/",
  component: DashboardPage,
});

const packsRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: "/packs",
  component: PacksPage,
  validateSearch: (search: Record<string, unknown>) => ({
    wizard: parseWizardSearch(search.wizard),
    pack: normalizeSearchString(search.pack),
  }),
});

const agentsRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: "/agents",
  component: AgentsPage,
});

const pipelineRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: "/pipeline",
  component: PipelinePage,
});

const jobsRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: "/jobs",
  component: JobsPage,
  validateSearch: (search: Record<string, unknown>) => ({
    id: typeof search.id === "string" ? search.id : undefined,
  }),
});

const artifactsRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: "/artifacts",
  component: ArtifactsPage,
});

const artifactDetailRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: "/artifacts/$hash",
  component: ArtifactDetailPage,
});

const verifyRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: "/verify",
  component: VerifyPage,
  validateSearch: (search: Record<string, unknown>) => ({
    hash: typeof search.hash === "string" ? search.hash : undefined,
    job: typeof search.job === "string" ? search.job : undefined,
  }),
});

const auditRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: "/audit",
  component: AuditPage,
});

const governanceRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: "/governance",
  component: GovernancePage,
  validateSearch: (search: Record<string, unknown>) => ({
    proposal:
      typeof search.proposal === "string" ? search.proposal : undefined,
    tab:
      search.tab === "specs" || search.tab === "proposals"
        ? search.tab
        : undefined,
  }),
});

const systemRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: "/system",
  component: SystemPage,
  validateSearch: (search: Record<string, unknown>) => ({
    tab:
      search.tab === "health" ||
      search.tab === "backups" ||
      search.tab === "integrations"
        ? search.tab
        : undefined,
  }),
});

const settingsRoute = createRoute({
  getParentRoute: () => shellRoute,
  path: "/settings",
  component: SettingsPage,
});

const setupPreviewRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/setup-preview",
  component: SetupPage,
});

const bootstrapPreviewRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/bootstrap-preview",
  component: BootstrapPage,
});

const catchAllRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "$",
  component: () => <Navigate to="/" />,
});

const routeTree = rootRoute.addChildren([
  bootstrapRoute,
  setupRoute,
  onboardingRoute,
  ...(import.meta.env.DEV
    ? [setupPreviewRoute, bootstrapPreviewRoute]
    : []),
  shellRoute.addChildren([
    dashboardRoute,
    packsRoute,
    agentsRoute,
    pipelineRoute,
    jobsRoute,
    artifactDetailRoute,
    artifactsRoute,
    verifyRoute,
    auditRoute,
    governanceRoute,
    systemRoute,
    settingsRoute,
  ]),
  catchAllRoute,
]);

export const router = createRouter({
  routeTree,
  context: {
    onboarded: readOnboardedSync(),
    sovereignReady: false,
  } satisfies RouterContext,
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}