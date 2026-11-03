import type { RouteObject } from "react-router";

import { AppIndexRedirect } from "../features/app-shell/AppIndexRedirect";
import { CashFlowPage } from "../features/analytics/CashFlowPage";
import { ProfitLossPage } from "../features/analytics/ProfitLossPage";
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
import { TransactionsPage } from "../features/transactions/TransactionsPage";

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
            // `handle.title` is shown in the top bar of the app shell.
            children: [
              { index: true, element: <DashboardPage />, handle: { title: "Overview" } },
              {
                path: "transactions",
                element: <TransactionsPage />,
                handle: { title: "Transactions" },
              },
              { path: "cash-flow", element: <CashFlowPage />, handle: { title: "Cash flow" } },
              {
                path: "profit-loss",
                element: <ProfitLossPage />,
                handle: { title: "Profit & loss" },
              },
            ],
          },
        ],
      },
      // The design preview exists only in development builds; production never includes it.
      ...(import.meta.env.DEV ? [{ path: "/design", element: <DesignPreviewPage /> }] : []),
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
