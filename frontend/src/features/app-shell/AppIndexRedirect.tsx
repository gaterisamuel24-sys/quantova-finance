import { Navigate } from "react-router";

import { FullPageSpinner } from "../../components/FullPageSpinner";
import { Alert } from "../../components/ui/Alert";
import { useOrganizations } from "../organizations/api";
import { lastOrganizationId } from "../organizations/last-organization";

/** /app: send the user to their last organization, their first one, or onboarding. */
export function AppIndexRedirect() {
  const { data: organizations, isPending, isError } = useOrganizations();

  if (isPending) return <FullPageSpinner />;
  if (isError) {
    return (
      <main className="mx-auto max-w-md px-4 py-24">
        <Alert tone="error" title="We couldn't load your organizations.">
          Refresh the page to try again.
        </Alert>
      </main>
    );
  }
  if (organizations.length === 0) return <Navigate to="/app/new" replace />;

  const remembered = lastOrganizationId();
  const target = organizations.find((org) => org.id === remembered) ?? organizations[0];
  return <Navigate to={`/app/${target.id}`} replace />;
}
