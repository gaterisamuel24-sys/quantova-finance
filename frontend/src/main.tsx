import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router";

import "@fontsource-variable/inter";
import "@fontsource-variable/jetbrains-mono";
import "./styles/globals.css";

import { routes } from "./app/routes";
import { ThemeProvider } from "./app/theme/ThemeProvider";

const router = createBrowserRouter(routes);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <RouterProvider router={router} />
    </ThemeProvider>
  </StrictMode>,
);
