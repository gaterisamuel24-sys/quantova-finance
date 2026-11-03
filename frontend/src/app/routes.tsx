import type { RouteObject } from "react-router";

import { LandingPage } from "../features/marketing/LandingPage";
import { DesignPreviewPage } from "../features/system/DesignPreviewPage";
import { NotFoundPage } from "../features/system/NotFoundPage";
import { PlaceholderPage } from "../features/system/PlaceholderPage";

/** Every URL in the app and the page it renders. */
export const routes: RouteObject[] = [
  { path: "/", element: <LandingPage /> },
  { path: "/login", element: <PlaceholderPage title="Sign in" /> },
  { path: "/register", element: <PlaceholderPage title="Create your account" /> },
  // The design preview exists only in development builds; production never includes it.
  ...(import.meta.env.DEV ? [{ path: "/design", element: <DesignPreviewPage /> }] : []),
  { path: "*", element: <NotFoundPage /> },
];
