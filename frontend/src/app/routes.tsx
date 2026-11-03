import type { RouteObject } from "react-router";

import { LoginPage } from "../features/auth/LoginPage";
import { RegisterPage } from "../features/auth/RegisterPage";
import { GuestOnly, RequireAuth } from "../features/auth/route-guards";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { LandingPage } from "../features/marketing/LandingPage";
import { DesignPreviewPage } from "../features/system/DesignPreviewPage";
import { NotFoundPage } from "../features/system/NotFoundPage";

/** Every URL in the app and the page it renders. */
export const routes: RouteObject[] = [
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
    children: [{ path: "/app", element: <DashboardPage /> }],
  },
  // The design preview exists only in development builds; production never includes it.
  ...(import.meta.env.DEV ? [{ path: "/design", element: <DesignPreviewPage /> }] : []),
  { path: "*", element: <NotFoundPage /> },
];
