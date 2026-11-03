import type { RouteObject } from "react-router";

import { AppIndexRedirect } from "../features/app-shell/AppIndexRedirect";
import { AppShell } from "../features/app-shell/AppShell";
import { LoginPage } from "../features/auth/LoginPage";
import { RegisterPage } from "../features/auth/RegisterPage";
import { GuestOnly, RequireAuth } from "../features/auth/route-guards";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { LandingPage } from "../features/marketing/LandingPage";
import { CreateOrganizationPage } from "../features/organizations/CreateOrganizationPage";
import { DesignPreviewPage } from "../features/system/DesignPreviewPage";
import { NotFoundPage } from "../features/system/NotFoundPage";
import { RouteErrorPage } from "../features/system/RouteErrorPage";

/** Every URL in the app and the page it renders. */
export const routes: RouteObject[] = [
  {
    // Any unexpected error in any page below renders RouteErrorPage instead of a blank screen.
    errorElement: <RouteErrorPage />,
    children: [
      { path: "/", element: <LandingPage /> },
      {
        element: <GuestOnly />,
        children: [
          { path: "/login", element: <LoginPage /> },
          { path: "/register", element: <RegisterPage /> },
        ],
      },
      {
        element: <RequireAuth />,
        children: [
          { path: "/app", element: <AppIndexRedirect /> },
          { path: "/app/new", element: <CreateOrganizationPage /> },
          {
            path: "/app/:orgId",
            element: <AppShell />,
            children: [{ index: true, element: <DashboardPage /> }],
          },
        ],
      },
      // The design preview exists only in development builds; production never includes it.
      ...(import.meta.env.DEV ? [{ path: "/design", element: <DesignPreviewPage /> }] : []),
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
