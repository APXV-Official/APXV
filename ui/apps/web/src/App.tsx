import { setUnauthorizedHandler } from "@apxv/api-client";
import { RouterProvider } from "@tanstack/react-router";
import { useEffect, useRef } from "react";
import { useApp } from "./context/AppContext";
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
        const path = router.state.location.pathname;
        const firstRun = getFirstRunPath();
        if (path !== firstRun && path !== "/onboarding") {
          void router.navigate({
            to: firstRun,
            search: { redirect: path },
          });
        }
      })();
    });
    return () => setUnauthorizedHandler(null);
  }, [invalidateSession]);

  return (
    <RouterProvider router={router} context={{ onboarded, sovereignReady }} />
  );
}