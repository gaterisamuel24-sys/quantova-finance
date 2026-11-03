import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "../../lib/api/client";
import { toApiError } from "../../lib/api/errors";
import type { components } from "../../lib/api/schema";

export type Billing = components["schemas"]["BillingResponse"];
export type Plan = components["schemas"]["PlanResponse"];
export type PlanId = Plan["id"];

export const billingKeys = {
  detail: (orgId: string) => ["org", orgId, "billing"] as const,
};

/** Plan, status and usage. `poll` refetches every few seconds (while waiting for a payment). */
export function useBilling(orgId: string, { poll = false }: { poll?: boolean } = {}) {
  return useQuery({
    queryKey: billingKeys.detail(orgId),
    queryFn: async () => {
      const { data, error, response } = await api.GET("/api/v1/orgs/{org_id}/billing", {
        params: { path: { org_id: orgId } },
      });
      if (data === undefined) throw toApiError(error, response, "Could not load billing.");
      return data;
    },
    refetchInterval: poll ? 3000 : false,
  });
}

/** Ask the server for a hosted checkout page for a plan. Returns its URL. */
export function useStartCheckout(orgId: string) {
  return useMutation({
    mutationFn: async (plan: PlanId) => {
      const { data, error, response } = await api.POST("/api/v1/orgs/{org_id}/billing/checkout", {
        params: { path: { org_id: orgId } },
        body: { plan },
      });
      if (data === undefined) throw toApiError(error, response, "Could not start the checkout.");
      return data.url;
    },
  });
}

/** Ask the server for the provider's billing portal. Returns its URL. */
export function useOpenPortal(orgId: string) {
  return useMutation({
    mutationFn: async () => {
      const { data, error, response } = await api.POST("/api/v1/orgs/{org_id}/billing/portal", {
        params: { path: { org_id: orgId } },
      });
      if (data === undefined) throw toApiError(error, response, "Could not open billing.");
      return data.url;
    },
  });
}
