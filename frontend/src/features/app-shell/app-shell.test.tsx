import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { createFakeBackend, makeOrganization } from "../../test/fake-backend";
import { renderRoute } from "../../test/render";

describe("app shell", () => {
  it("guides a new user to create an organization, then opens its dashboard", async () => {
    const { router } = renderRoute("/app", createFakeBackend({ signedIn: true }));

    expect(
      await screen.findByRole("heading", { name: "Create your first organization" }),
    ).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Organization name"), {
      target: { value: "Acme Ltd" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create organization" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Acme Ltd" })).toBeTruthy();
    expect(router.state.location.pathname).toMatch(/^\/app\/[0-9a-f-]{36}$/);
  });

  it("opens the first organization and switches between organizations", async () => {
    const acme = makeOrganization("Acme Ltd");
    const beta = makeOrganization("Beta Holdings", "KES");
    renderRoute("/app", createFakeBackend({ signedIn: true, organizations: [acme, beta] }));

    expect(await screen.findByRole("heading", { level: 1, name: "Acme Ltd" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /switch organization/i }));
    fireEvent.click(screen.getByRole("link", { name: "Beta Holdings" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Beta Holdings" })).toBeTruthy();
  });

  it("reopens the organization used last", async () => {
    const acme = makeOrganization("Acme Ltd");
    const beta = makeOrganization("Beta Holdings");
    localStorage.setItem("quantova-last-organization", beta.id);

    renderRoute("/app", createFakeBackend({ signedIn: true, organizations: [acme, beta] }));

    expect(await screen.findByRole("heading", { level: 1, name: "Beta Holdings" })).toBeTruthy();
  });

  it("shows 'not found' for an organization the user cannot access", async () => {
    renderRoute(
      `/app/${crypto.randomUUID()}`,
      createFakeBackend({ signedIn: true, organizations: [makeOrganization("Acme Ltd")] }),
    );

    expect(await screen.findByRole("heading", { name: "Organization not found" })).toBeTruthy();
  });
});
