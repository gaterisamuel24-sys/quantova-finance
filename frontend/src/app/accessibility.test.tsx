import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { createFakeBackend, makeOrganization } from "../test/fake-backend";
import { renderRoute } from "../test/render";

async function expectWorkingSkipLink() {
  const skipLink = await screen.findByRole("link", { name: "Skip to main content" });
  expect(skipLink.getAttribute("href")).toBe("#main-content");
  const target = document.getElementById("main-content");
  expect(target?.tagName).toBe("MAIN");
  expect(target?.getAttribute("tabindex")).toBe("-1");
}

describe("accessibility", () => {
  it("the landing page has a working skip link", async () => {
    renderRoute("/");

    await expectWorkingSkipLink();
  });

  it("the app shell has a working skip link", async () => {
    const organization = makeOrganization("Acme Ltd");
    renderRoute(
      `/app/${organization.id}`,
      createFakeBackend({ signedIn: true, organizations: [organization] }),
    );

    await screen.findByRole("heading", { level: 1, name: "Acme Ltd" });
    await expectWorkingSkipLink();
  });
});
