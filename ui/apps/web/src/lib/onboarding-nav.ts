/** Shell paths valid for post-onboarding redirect (must match router). */
export const ONBOARDING_SHELL_PATHS = [
  "/",
  "/packs",
  "/agents",
  "/pipeline",
  "/jobs",
  "/artifacts",
  "/verify",
  "/audit",
  "/governance",
  "/system",
  "/settings",
] as const;

export type OnboardingShellPath = (typeof ONBOARDING_SHELL_PATHS)[number];

export type OnboardingRedirect = {
  to: OnboardingShellPath;
  search: Record<string, unknown>;
};

/** Serialize pathname + search for storage in ?redirect= */
export function shellRedirectTarget(
  pathname: string,
  search: Record<string, unknown>,
): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(search)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }
  const qs = params.toString();
  return qs ? `${pathname}?${qs}` : pathname;
}

export function parseOnboardingRedirect(
  redirectTo: string | undefined,
): OnboardingRedirect {
  if (!redirectTo) return { to: "/", search: {} };

  const qIndex = redirectTo.indexOf("?");
  const path = qIndex >= 0 ? redirectTo.slice(0, qIndex) : redirectTo;
  const query = qIndex >= 0 ? redirectTo.slice(qIndex + 1) : "";

  if (!(ONBOARDING_SHELL_PATHS as readonly string[]).includes(path)) {
    return { to: "/", search: {} };
  }

  const params = new URLSearchParams(query);
  const to = path as OnboardingShellPath;

  switch (to) {
    case "/packs":
      return {
        to,
        search: {
          wizard: params.get("wizard") === "1" ? ("1" as const) : undefined,
          pack: params.get("pack") ?? undefined,
        },
      };
    case "/jobs":
      return { to, search: { id: params.get("id") ?? undefined } };
    case "/verify":
      return {
        to,
        search: {
          hash: params.get("hash") ?? undefined,
          job: params.get("job") ?? undefined,
        },
      };
    case "/governance": {
      const tab = params.get("tab");
      const validTab =
        tab === "proposals" ? "proposals" : tab === "specs" ? "specs" : undefined;
      return {
        to,
        search: {
          tab: validTab,
          proposal: params.get("proposal") ?? undefined,
        },
      };
    }
    case "/system": {
      const tab = params.get("tab");
      const validTab = ["health", "backups", "integrations"].includes(tab ?? "")
        ? tab
        : undefined;
      return { to, search: { tab: validTab } };
    }
    default:
      return { to, search: {} };
  }
}

/** @deprecated Use parseOnboardingRedirect */
export function onboardingRedirectTarget(
  redirectTo: string | undefined,
): OnboardingShellPath {
  return parseOnboardingRedirect(redirectTo).to;
}