import { Link } from "react-router";

import { PublicFooter } from "../../components/layout/PublicFooter";
import { PublicHeader } from "../../components/layout/PublicHeader";
import { buttonClasses } from "../../components/ui/button-styles";

export function NotFoundPage() {
  return (
    <>
      <title>Page not found · Quantova Finance</title>
      <PublicHeader />
      <main className="mx-auto flex min-h-[60vh] max-w-xl flex-col items-center justify-center px-4 text-center">
        <p className="font-mono text-sm text-brand">404</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Page not found</h1>
        <p className="mt-3 text-muted-foreground">
          The page you are looking for does not exist or has moved.
        </p>
        <Link to="/" className={buttonClasses({ className: "mt-8" })}>
          Back to home
        </Link>
      </main>
      <PublicFooter />
    </>
  );
}
