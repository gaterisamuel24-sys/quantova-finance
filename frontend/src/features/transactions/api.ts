import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../lib/api/client";
import { authFetch } from "../../lib/api/auth-fetch";
import { toApiError } from "../../lib/api/errors";
import type { components } from "../../lib/api/schema";
import { API_ORIGIN } from "../../lib/config";
import { filtersToQuery, type TransactionFilters } from "./filters";

export type Account = components["schemas"]["AccountResponse"];
export type Category = components["schemas"]["CategoryResponse"];
export type Transaction = components["schemas"]["TransactionResponse"];
export type TransactionPage = components["schemas"]["TransactionPage"];
export type TransactionCreate = components["schemas"]["TransactionCreate"];
export type TransactionUpdate = components["schemas"]["TransactionUpdate"];
export type ImportReport = components["schemas"]["ImportReport"];

export const PAGE_SIZE = 25;

// Cache keys. Everything for one organization starts with ["org", orgId], so after a
// change we can refresh that organization's data without touching any other.
export const ledgerKeys = {
  org: (orgId: string) => ["org", orgId] as const,
  accounts: (orgId: string) => ["org", orgId, "accounts"] as const,
  categories: (orgId: string) => ["org", orgId, "categories"] as const,
  transactions: (orgId: string) => ["org", orgId, "transactions"] as const,
  transactionList: (orgId: string, filters: TransactionFilters) =>
    ["org", orgId, "transactions", filters] as const,
};

export function useAccounts(orgId: string) {
  return useQuery({
    queryKey: ledgerKeys.accounts(orgId),
    queryFn: async () => {
      const { data, error, response } = await api.GET("/api/v1/orgs/{org_id}/accounts", {
        params: { path: { org_id: orgId } },
      });
      if (data === undefined) throw toApiError(error, response, "Could not load accounts.");
      return data;
    },
  });
}

export function useCategories(orgId: string) {
  return useQuery({
    queryKey: ledgerKeys.categories(orgId),
    queryFn: async () => {
      const { data, error, response } = await api.GET("/api/v1/orgs/{org_id}/categories", {
        params: { path: { org_id: orgId } },
      });
      if (data === undefined) throw toApiError(error, response, "Could not load categories.");
      return data;
    },
  });
}

export function useTransactions(orgId: string, filters: TransactionFilters) {
  return useQuery({
    queryKey: ledgerKeys.transactionList(orgId, filters),
    queryFn: async () => {
      const { data, error, response } = await api.GET("/api/v1/orgs/{org_id}/transactions", {
        params: {
          path: { org_id: orgId },
          query: { ...filtersToQuery(filters), page_size: PAGE_SIZE },
        },
      });
      if (data === undefined) throw toApiError(error, response, "Could not load transactions.");
      return data;
    },
    // Keep showing the current page while the next one loads, instead of flashing a spinner.
    placeholderData: keepPreviousData,
  });
}

/** After any change, refresh everything derived from this organization's ledger. */
function useRefreshLedger(orgId: string) {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ledgerKeys.org(orgId) });
}

export function useCreateTransaction(orgId: string) {
  const refresh = useRefreshLedger(orgId);
  return useMutation({
    mutationFn: async (body: TransactionCreate) => {
      const { data, error, response } = await api.POST("/api/v1/orgs/{org_id}/transactions", {
        params: { path: { org_id: orgId } },
        body,
      });
      if (data === undefined) throw toApiError(error, response, "Could not save the transaction.");
      return data;
    },
    onSuccess: refresh,
  });
}

export function useUpdateTransaction(orgId: string) {
  const refresh = useRefreshLedger(orgId);
  return useMutation({
    mutationFn: async ({ id, changes }: { id: string; changes: TransactionUpdate }) => {
      const { data, error, response } = await api.PATCH(
        "/api/v1/orgs/{org_id}/transactions/{transaction_id}",
        { params: { path: { org_id: orgId, transaction_id: id } }, body: changes },
      );
      if (data === undefined) throw toApiError(error, response, "Could not save the transaction.");
      return data;
    },
    onSuccess: refresh,
  });
}

export function useDeleteTransaction(orgId: string) {
  const refresh = useRefreshLedger(orgId);
  return useMutation({
    mutationFn: async (id: string) => {
      const { error, response } = await api.DELETE(
        "/api/v1/orgs/{org_id}/transactions/{transaction_id}",
        { params: { path: { org_id: orgId, transaction_id: id } } },
      );
      if (!response.ok) throw toApiError(error, response, "Could not delete the transaction.");
    },
    onSuccess: refresh,
  });
}

// ── CSV import ────────────────────────────────────────
// File uploads are multipart/form-data, which the typed JSON client does not build for us,
// so these two calls use authFetch directly. They still send the access token and retry
// once after refreshing it, exactly like every other API call.

function importUrl(orgId: string, suffix = ""): string {
  return `${API_ORIGIN}/api/v1/orgs/${encodeURIComponent(orgId)}/transactions/import${suffix}`;
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

/** Upload a CSV file. With dryRun the server only checks it and imports nothing. */
export function useImportTransactions(orgId: string) {
  const refresh = useRefreshLedger(orgId);
  return useMutation({
    mutationFn: async ({ file, dryRun }: { file: File; dryRun: boolean }) => {
      const form = new FormData();
      form.append("file", file);
      const response = await authFetch(
        new Request(importUrl(orgId, `?dry_run=${dryRun}`), {
          method: "POST",
          body: form,
          credentials: "include",
        }),
      );
      const body = await readJson(response);
      if (!response.ok) throw toApiError(body, response, "Could not read the file.");
      return body as ImportReport;
    },
    onSuccess: (report) => {
      if (report.status === "imported") void refresh();
    },
  });
}

/** Download the CSV template. It needs the access token, so a plain link would not work. */
export async function downloadImportTemplate(orgId: string): Promise<void> {
  const response = await authFetch(
    new Request(importUrl(orgId, "/template"), { credentials: "include" }),
  );
  if (!response.ok) {
    throw toApiError(await readJson(response), response, "Could not download the template.");
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = "quantova-transactions-template.csv";
  link.click();
  URL.revokeObjectURL(url);
}
