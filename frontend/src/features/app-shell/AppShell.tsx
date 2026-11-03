import { useCallback, useEffect, useState } from "react";
import { Link, Outlet, useParams } from "react-router";

import { FullPageSpinner } from "../../components/FullPageSpinner";
import { SkipLink } from "../../components/SkipLink";
import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { buttonClasses } from "../../components/ui/button-styles";
import { useOrganizations } from "../organizations/api";
import { rememberLastOrganization } from "../organizations/last-organization";
import { MobileNav } from "./MobileNav";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function AppShell() {
  const { orgId } = useParams();
  const { data: organizations, isPending, isError, refetch } = useOrganizations();
  const [navOpen, setNavOpen] = useState(false);
  const closeNav = useCallback(() => setNavOpen(false), []);
  const organization = organizations?.find((candidate) => candidate.id === orgId);

  useEffect(() => {
    if (organization) rememberLastOrganization(organization.id);
  }, [organization]);

  if (isPending) return <FullPageSpinner />;
  if (isError) {
    return (
      <main className="mx-auto max-w-md px-4 py-24">
        <Alert tone="error" title="We couldn't load your organizations.">
          Check your connection and try again.
        </Alert>
        <Button className="mt-4" variant="secondary" onClick={() => void refetch()}>
          Try again
        </Button>
      </main>
    );
  }
  if (organization === undefined) {
    // Matches the API: organizations you can't access look exactly like ones that don't exist.
    return (
      <main className="mx-auto max-w-md px-4 py-24 text-center">
        <title>Organization not found · Quantova Finance</title>
        <h1 className="text-2xl font-semibold tracking-tight">Organization not found</h1>
        <p className="mt-2 text-muted-foreground">
          It doesn't exist, or you are not a member of it.
        </p>
        <Link to="/app" className={buttonClasses({ className: "mt-8" })}>
          Go to your workspace
        </Link>
      </main>
    );
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[16rem_minmax(0,1fr)]">
      <SkipLink />
      <div className="hidden lg:sticky lg:top-0 lg:block lg:h-screen">
        <Sidebar organization={organization} organizations={organizations} />
      </div>
      {navOpen && (
        <MobileNav onClose={closeNav}>
          <Sidebar
            organization={organization}
            organizations={organizations}
            onNavigate={closeNav}
          />
        </MobileNav>
      )}
      <div className="flex min-w-0 flex-col">
        <TopBar title="Overview" onOpenNav={() => setNavOpen(true)} />
        <main
          id="main-content"
          tabIndex={-1}
          className="flex-1 px-4 py-8 outline-none sm:px-6 lg:px-8"
        >
          <Outlet context={organization} />
        </main>
      </div>
    </div>
  );
}
