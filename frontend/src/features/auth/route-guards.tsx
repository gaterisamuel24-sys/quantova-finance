import { Navigate, Outlet, useLocation } from "react-router";

import { FullPageSpinner } from "../../components/FullPageSpinner";
import { useAuth } from "./auth-context";
import { safeRedirect } from "./redirect";

/** Pages inside require a session; visitors are sent to /login and returned afterwards. */
export function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") return <FullPageSpinner />;
  if (status === "anonymous") {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  return <Outlet />;
}

/** Login and register pages; signed-in users are sent on to where they were going. */
export function GuestOnly() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") return <FullPageSpinner />;
  if (status === "authenticated") return <Navigate to={safeRedirect(location.state)} replace />;
  return <Outlet />;
}
