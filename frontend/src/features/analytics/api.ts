import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { api } from "../../lib/api/client";
import { toApiError } from "../../lib/api/errors";
import type { components } from "../../lib/api/schema";
import type { Granularity, Period } from "./periods";

export type Summary = components["schemas"]["SummaryResponse"];
export type CashFlow = components["schemas"]["CashFlowResponse"];
export type CashFlowPoint = components["schemas"]["CashFlowPoint"];
export type ProfitLoss = components["schemas"]["ProfitLossResponse"];
export type CategorySection = components["schemas"]["CategorySection"];

// Keys start with ["org", orgId] like the ledger's, so adding, editing, deleting or
// importing transactions refreshes these figures automatically.
const analyticsKeys = {
  summary: (orgId: string, period: Period) =>
    ["org", orgId, "analytics", "summary", period] as const,
  cashFlow: (orgId: string, period: Period, granularity: Granularity) =>
    ["org", orgId, "analytics", "cash-flow", period, granularity] as const,
  profitLoss: (orgId: string, period: Period) =>
    ["org", orgId, "analytics", "profit-loss", period] as const,
};

export function useSummary(orgId: string, period: Period) {
  return useQuery({
    queryKey: analyticsKeys.summary(orgId, period),
    queryFn: async () => {
      const { data, error, response } = await api.GET("/api/v1/orgs/{org_id}/analytics/summary", {
        params: { path: { org_id: orgId }, query: { period } },
      });
      if (data === undefined) throw toApiError(error, response, "Could not load the summary.");
      return data;
    },
    placeholderData: keepPreviousData,
  });
}

export function useCashFlow(orgId: string, period: Period, granularity: Granularity) {
  return useQuery({
    queryKey: analyticsKeys.cashFlow(orgId, period, granularity),
    queryFn: async () => {
      const { data, error, response } = await api.GET("/api/v1/orgs/{org_id}/analytics/cash-flow", {
        params: { path: { org_id: orgId }, query: { period, granularity } },
      });
      if (data === undefined) throw toApiError(error, response, "Could not load cash flow.");
      return data;
    },
    placeholderData: keepPreviousData,
  });
}

export function useProfitLoss(orgId: string, period: Period) {
  return useQuery({
    queryKey: analyticsKeys.profitLoss(orgId, period),
    queryFn: async () => {
      const { data, error, response } = await api.GET(
        "/api/v1/orgs/{org_id}/analytics/profit-loss",
        { params: { path: { org_id: orgId }, query: { period } } },
      );
      if (data === undefined) throw toApiError(error, response, "Could not load profit & loss.");
      return data;
    },
    placeholderData: keepPreviousData,
  });
}
