import { render } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router";

import { routes } from "../app/routes";
import { ThemeProvider } from "../app/theme/ThemeProvider";

/** Render the real app at a given URL, with the same providers as main.tsx. */
export function renderRoute(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return render(
    <ThemeProvider>
      <RouterProvider router={router} />
    </ThemeProvider>,
  );
}
