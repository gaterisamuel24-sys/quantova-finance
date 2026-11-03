import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderRoute } from "../test/render";

describe("routes", () => {
  it("shows the landing page at /", async () => {
    renderRoute("/");

    const heading = await screen.findByRole("heading", { level: 1 });
    expect(heading.textContent).toContain("Understand your numbers");
  });

  it("links the calls to action to registration and sign-in", async () => {
    renderRoute("/");

    const getStarted = await screen.findAllByRole("link", { name: /get started/i });
    const signIn = screen.getAllByRole("link", { name: "Sign in" });

    expect(getStarted.every((link) => link.getAttribute("href") === "/register")).toBe(true);
    expect(signIn.every((link) => link.getAttribute("href") === "/login")).toBe(true);
  });

  it("shows a not-found page for unknown URLs", async () => {
    renderRoute("/this-page-does-not-exist");

    const heading = await screen.findByRole("heading", { level: 1 });
    expect(heading.textContent).toBe("Page not found");
  });
});
