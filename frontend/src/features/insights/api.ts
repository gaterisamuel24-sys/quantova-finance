import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api/client";
import { toApiError } from "../../lib/api/errors";
import type { components } from "../../lib/api/schema";
import type { Period } from "../analytics/periods";

export type Insight = components["schemas"]["InsightResponse"];
export type InsightList = components["schemas"]["InsightList"];
export type Observation = components["schemas"]["Observation"];
export type Suggestion = components["schemas"]["Suggestion"];
export type Fact = components["schemas"]["FactResponse"];

const insightKeys = {
  list: (orgId: string) => ["org", orgId, "insights"] as const,
};

export function useInsights(orgId: string) {
  return useQuery({
    queryKey: insightKeys.list(orgId),
    queryFn: async () => {
      const { data, error, response } = await api.GET("/api/v1/orgs/{org_id}/insights", {
        params: { path: { org_id: orgId } },
      });
      if (data === undefined) throw toApiError(error, response, "Could not load insights.");
      return data;
    },
  });
}

/** Ask the server to generate an insight. This calls the AI service and counts toward the daily limit. */
export function useGenerateInsight(orgId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (period: Period) => {
      const { data, error, response } = await api.POST("/api/v1/orgs/{org_id}/insights", {
        params: { path: { org_id: orgId } },
        body: { period },
      });
      if (data === undefined) throw toApiError(error, response, "Could not generate insights.");
      return data;
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: insightKeys.list(orgId) }),
  });
}
