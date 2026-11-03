import { json, type FetchHandler } from "./fake-api";

export const PASSWORD = "correct horse battery staple";

type FakeUser = {
  id: string;
  email: string;
  full_name: string;
  is_email_verified: boolean;
  platform_role: "user";
  created_at: string;
};

export type FakeOrganization = {
  id: string;
  name: string;
  slug: string;
  base_currency: string;
  fiscal_year_start_month: number;
  created_at: string;
  my_role: "owner";
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

export function makeOrganization(name: string, baseCurrency = "USD"): FakeOrganization {
  return {
    id: crypto.randomUUID(),
    name,
    slug: name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
    base_currency: baseCurrency,
    fiscal_year_start_month: 1,
    created_at: "2026-11-03T08:00:00Z",
    my_role: "owner",
  };
}

const token = (value: string) => ({ access_token: value, token_type: "bearer", expires_in: 900 });

type Options = { signedIn?: boolean; organizations?: FakeOrganization[] };

/** A simulated API that follows the real backend's rules for auth and organizations. */
export function createFakeBackend({
  signedIn = false,
  organizations = [],
}: Options = {}): FetchHandler {
  const amina = makeUser("amina@example.com", "Amina Otieno");
  const accounts = new Map([[amina.email, { password: PASSWORD, user: amina }]]);
  const orgs = [...organizations];
  let current: FakeUser | null = signedIn ? amina : null;

  return async (request) => {
    const path = new URL(request.url).pathname;
    const authorized = current !== null && request.headers.has("Authorization");

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
        return authorized ? json(200, current) : json(401, { detail: "Not authenticated" });
      case "/api/v1/auth/logout":
        current = null;
        return json(204);
      case "/api/v1/orgs": {
        if (!authorized) return json(401, { detail: "Not authenticated" });
        if (request.method === "GET") return json(200, orgs);
        const body = (await request.json()) as { name: string; base_currency?: string };
        const organization = makeOrganization(body.name, body.base_currency);
        orgs.push(organization);
        return json(201, organization);
      }
      default:
        return json(404, { detail: "Not Found" });
    }
  };
}
