import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";

import { routes } from "../app/routes";
import { ThemeProvider } from "../app/theme/ThemeProvider";
import { AuthProvider } from "../features/auth/AuthProvider";
import { json, stubFetch, type FetchHandler } from "./fake-api";

const SIGNED_OUT: FetchHandler = () => json(401, { detail: "Not authenticated" });

/** Render the real app at a URL, with the same providers as main.tsx and a fake backend. */
export function renderRoute(path: string, backend: FetchHandler = SIGNED_OUT) {
  const fetchMock = stubFetch(backend);
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const view = render(
    <ThemeProvider>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </ThemeProvider>,
  );
  return { ...view, router, fetchMock };
}
