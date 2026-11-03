import { useOutletContext } from "react-router";

import type { Organization } from "./api";

/** The organization of the current /app/{orgId} page. Only usable inside the app shell. */
export function useCurrentOrganization(): Organization {
  return useOutletContext<Organization>();
}
