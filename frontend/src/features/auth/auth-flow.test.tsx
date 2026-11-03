import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { createFakeBackend, PASSWORD } from "../../test/fake-backend";
import { renderRoute } from "../../test/render";

const ONBOARDING = { name: "Create your first organization" };
const SIGN_IN = { name: "Sign in to Quantova" };

async function fillAndSubmit(fields: Record<string, string>, submitLabel: string) {
  for (const [label, value] of Object.entries(fields)) {
    fireEvent.change(await screen.findByLabelText(label), { target: { value } });
  }
  fireEvent.click(screen.getByRole("button", { name: submitLabel }));
}

describe("authentication flow", () => {
  it("sends visitors to sign in, then on into the app", async () => {
    const { router } = renderRoute("/app", createFakeBackend());

    expect(await screen.findByRole("heading", SIGN_IN)).toBeTruthy();
    await fillAndSubmit({ Email: "amina@example.com", Password: PASSWORD }, "Sign in");

    expect(await screen.findByRole("heading", ONBOARDING)).toBeTruthy();
    expect(router.state.location.pathname).toBe("/app/new");
  });

  it("shows the server's message for a wrong password", async () => {
    renderRoute("/login", createFakeBackend());

    await fillAndSubmit({ Email: "amina@example.com", Password: "wrong-password-123" }, "Sign in");

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Incorrect email or password.",
    );
  });

  it("restores the session on reload using the refresh cookie", async () => {
    renderRoute("/login", createFakeBackend({ signedIn: true }));

    expect(await screen.findByRole("heading", ONBOARDING)).toBeTruthy();
  });

  it("signs out from the account menu and returns to sign in", async () => {
    renderRoute("/app/new", createFakeBackend({ signedIn: true }));

    fireEvent.click(await screen.findByRole("button", { name: "Account menu" }));
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));

    expect(await screen.findByRole("heading", SIGN_IN)).toBeTruthy();
  });

  it("rejects a short password before contacting the server", async () => {
    const { fetchMock } = renderRoute("/register", createFakeBackend());

    await fillAndSubmit(
      { "Full name": "Brian Kamau", Email: "brian@example.com", Password: "too-short" },
      "Create account",
    );

    expect(await screen.findByText("Use at least 12 characters.")).toBeTruthy();
    const urls = fetchMock.mock.calls.map(([input]) =>
      input instanceof Request ? input.url : String(input),
    );
    expect(urls.some((url) => url.includes("/auth/register"))).toBe(false);
  });

  it("creates an account and signs the new user in", async () => {
    renderRoute("/register", createFakeBackend());

    await fillAndSubmit(
      { "Full name": "Brian Kamau", Email: "brian@example.com", Password: PASSWORD },
      "Create account",
    );

    expect(await screen.findByRole("heading", ONBOARDING)).toBeTruthy();
  });
});
