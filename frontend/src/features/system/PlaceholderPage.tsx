import { Link } from "react-router";

import { PublicHeader } from "../../components/layout/PublicHeader";
import { buttonClasses } from "../../components/ui/button-styles";

export function PlaceholderPage({ title }: { title: string }) {
  return (
    <>
      <title>{`${title} · Quantova Finance`}</title>
      <PublicHeader />
      <main className="mx-auto max-w-xl px-4 py-24 text-center">
        <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-3 text-muted-foreground">This page is being built in the next step.</p>
        <Link to="/" className={buttonClasses({ variant: "secondary", className: "mt-8" })}>
          Back to home
        </Link>
      </main>
    </>
  );
}
