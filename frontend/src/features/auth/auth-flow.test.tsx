import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { json, type FetchHandler } from "../../test/fake-api";
import { renderRoute } from "../../test/render";

const PASSWORD = "correct horse battery staple";

type FakeUser = {
  id: string;
  email: string;
  full_name: string;
  is_email_verified: boolean;
  platform_role: "user";
  created_at: string;
};

function makeUser(email: string, fullName: string): FakeUser {
  return {
    id: crypto.randomUUID(),
    email,
    full_name: fullName,
    is_email_verified: false,
    platform_role: "user",
    created_at: "2026-11-03T08:00:00Z",
  };
}

const token = (value: string) => ({ access_token: value, token_type: "bearer", expires_in: 900 });

/** A small simulated auth backend that follows the real API's rules. */
function fakeAuthBackend({ hasSessionCookie = false } = {}): FetchHandler {
  const amina = makeUser("amina@example.com", "Amina Otieno");
  const accounts = new Map([[amina.email, { password: PASSWORD, user: amina }]]);
  let current: FakeUser | null = hasSessionCookie ? amina : null;

  return async (request) => {
    const path = new URL(request.url).pathname;
    switch (path) {
      case "/api/v1/auth/refresh":
        return current
          ? json(200, token("restored"))
          : json(401, { detail: "Session expired. Please log in again." });
      case "/api/v1/auth/login": {
        const body = (await request.json()) as { email: string; password: string };
        const account = accounts.get(body.email);
        if (account?.password !== body.password) {
          return json(401, { detail: "Incorrect email or password." });
        }
        current = account.user;
        return json(200, token("signed-in"));
      }
      case "/api/v1/auth/register": {
        const body = (await request.json()) as {
          email: string;
          password: string;
          full_name: string;
        };
        const user = makeUser(body.email, body.full_name);
        accounts.set(body.email, { password: body.password, user });
        return json(201, user);
      }
      case "/api/v1/auth/me":
        return current && request.headers.get("Authorization")
          ? json(200, current)
          : json(401, { detail: "Not authenticated" });
      case "/api/v1/auth/logout":
        current = null;
        return json(204);
      default:
        return json(404, { detail: "Not Found" });
    }
  };
}

async function fillAndSubmit(fields: Record<string, string>, submitLabel: string) {
  for (const [label, value] of Object.entries(fields)) {
    fireEvent.change(await screen.findByLabelText(label), { target: { value } });
  }
  fireEvent.click(screen.getByRole("button", { name: submitLabel }));
}

describe("authentication flow", () => {
  it("sends visitors to sign in, then back to the page they wanted", async () => {
    const { router } = renderRoute("/app", fakeAuthBackend());

    expect(await screen.findByRole("heading", { name: "Sign in to Quantova" })).toBeTruthy();
    await fillAndSubmit({ Email: "amina@example.com", Password: PASSWORD }, "Sign in");

    expect(await screen.findByRole("heading", { name: "Welcome, Amina Otieno" })).toBeTruthy();
    expect(router.state.location.pathname).toBe("/app");
  });

  it("shows the server's message for a wrong password", async () => {
    renderRoute("/login", fakeAuthBackend());

    await fillAndSubmit({ Email: "amina@example.com", Password: "wrong-password-123" }, "Sign in");

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Incorrect email or password.",
    );
  });

  it("restores the session on reload using the refresh cookie", async () => {
    renderRoute("/login", fakeAuthBackend({ hasSessionCookie: true }));

    expect(await screen.findByRole("heading", { name: "Welcome, Amina Otieno" })).toBeTruthy();
  });

  it("signs out and returns to the sign-in page", async () => {
    renderRoute("/app", fakeAuthBackend({ hasSessionCookie: true }));

    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }));

    expect(await screen.findByRole("heading", { name: "Sign in to Quantova" })).toBeTruthy();
  });

  it("rejects a short password before contacting the server", async () => {
    const { fetchMock } = renderRoute("/register", fakeAuthBackend());

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
    renderRoute("/register", fakeAuthBackend());

    await fillAndSubmit(
      { "Full name": "Brian Kamau", Email: "brian@example.com", Password: PASSWORD },
      "Create account",
    );

    expect(await screen.findByRole("heading", { name: "Welcome, Brian Kamau" })).toBeTruthy();
  });
});
