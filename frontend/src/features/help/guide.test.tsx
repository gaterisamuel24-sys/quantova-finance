import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderRoute } from "../../test/render";

describe("user guide", () => {
  it("is public and explains the first steps", async () => {
    renderRoute("/guide");

    const heading = await screen.findByRole("heading", { level: 1 });
    expect(heading.textContent).toBe("How to use Quantova Finance");
    expect(screen.getByRole("heading", { name: "Create your account" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Who can do what" })).toBeTruthy();
  });

  it("is linked from the public pages", async () => {
    renderRoute("/");

    const links = await screen.findAllByRole("link", { name: /guide|how to use quantova/i });
    expect(links.length).toBeGreaterThan(0);
    expect(links.every((link) => link.getAttribute("href") === "/guide")).toBe(true);
  });
});
