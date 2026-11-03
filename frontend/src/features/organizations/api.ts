import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api/client";
import { toApiError } from "../../lib/api/errors";
import type { components } from "../../lib/api/schema";

export type Organization = components["schemas"]["OrganizationResponse"];
export type OrganizationCreate = components["schemas"]["OrganizationCreate"];

export const organizationKeys = {
  all: ["organizations"] as const,
};

/** The organizations the current user belongs to, with their role in each. */
export function useOrganizations() {
  return useQuery({
    queryKey: organizationKeys.all,
    queryFn: async () => {
      const { data, error, response } = await api.GET("/api/v1/orgs");
      if (data === undefined)
        throw toApiError(error, response, "Could not load your organizations.");
      return data;
    },
  });
}

export function useCreateOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: OrganizationCreate) => {
      const { data, error, response } = await api.POST("/api/v1/orgs", { body: input });
      if (data === undefined)
        throw toApiError(error, response, "Could not create the organization.");
      return data;
    },
    onSuccess: (organization) => {
      // Add the new organization to the cached list, so every screen sees it immediately.
      queryClient.setQueryData<Organization[]>(organizationKeys.all, (current) => [
        ...(current ?? []),
        organization,
      ]);
    },
  });
}
