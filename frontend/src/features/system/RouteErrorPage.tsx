import { useEffect } from "react";
import { useRouteError } from "react-router";

import { Button } from "../../components/ui/Button";
import { buttonClasses } from "../../components/ui/button-styles";

/** Shown instead of a blank screen when any page throws an unexpected error. */
export function RouteErrorPage() {
  const error = useRouteError();

  useEffect(() => {
    // Keep the technical details in the browser console for debugging; never show them to users.
    console.error("Unhandled route error:", error);
  }, [error]);

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-4 text-center">
      <title>Something went wrong · Quantova Finance</title>
      <p className="font-mono text-sm text-negative">Error</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight">Something went wrong</h1>
      <p className="mt-3 text-muted-foreground">
        An unexpected problem stopped this page from loading. Nothing was changed. Please try
        reloading.
      </p>
      <div className="mt-8 flex gap-3">
        <Button onClick={() => window.location.reload()}>Reload page</Button>
        <a href="/" className={buttonClasses({ variant: "secondary" })}>
          Go to home
        </a>
      </div>
    </main>
  );
}
