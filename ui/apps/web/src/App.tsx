import { setUnauthorizedHandler } from "@apxv/api-client";
import { RouterProvider } from "@tanstack/react-router";
import { useEffect, useRef } from "react";
import { useApp } from "./context/AppContext";
import { shellRedirectTarget } from "./lib/onboarding-nav";
import { getFirstRunPath } from "./lib/tauri";
import { router } from "./router";

export default function App() {
  const { onboarded, sovereignReady, invalidateSession } = useApp();
  const lastUnauthorizedAt = useRef(0);

  useEffect(() => {
    router.update({ context: { onboarded, sovereignReady } });
    void router.invalidate();
  }, [onboarded, sovereignReady]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      const now = Date.now();
      if (now - lastUnauthorizedAt.current < 3000) return;
      lastUnauthorizedAt.current = now;

      void (async () => {
        await invalidateSession();
        const { pathname, search } = router.state.location;
        const firstRun = getFirstRunPath();
        if (pathname !== firstRun && pathname !== "/onboarding") {
          router.update({
            context: { onboarded: false, sovereignReady },
          });
          await router.invalidate();
          void router.navigate({
            to: firstRun,
            search: {
              redirect: shellRedirectTarget(
                pathname,
                search as Record<string, unknown>,
              ),
            },
          });
        }
      })();
    });
    return () => setUnauthorizedHandler(null);
  }, [invalidateSession, sovereignReady]);

  return (
    <RouterProvider router={router} context={{ onboarded, sovereignReady }} />
  );
}