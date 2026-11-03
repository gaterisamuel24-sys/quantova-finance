import { describe, expect, it } from "vitest";

import {
  EMPTY_FILTERS,
  filtersFromParams,
  filtersToParams,
  filtersToQuery,
  hasActiveFilters,
  todayIso,
} from "./filters";

const ACCOUNT = "0193f2a0-1111-7000-8000-000000000001";

describe("transaction filters in the URL", () => {
  it("round-trips through URL parameters", () => {
    const filters = {
      ...EMPTY_FILTERS,
      q: "rent",
      kind: "expense" as const,
      accountId: ACCOUNT,
      dateFrom: "2026-01-01",
      dateTo: "2026-03-31",
      page: 3,
    };

    const params = filtersToParams(filters);

    expect(params.toString()).toBe(
      `q=rent&kind=expense&account=${ACCOUNT}&from=2026-01-01&to=2026-03-31&page=3`,
    );
    expect(filtersFromParams(params)).toEqual(filters);
  });

  it("leaves empty filters and page 1 out of the URL", () => {
    expect(filtersToParams(EMPTY_FILTERS).toString()).toBe("");
  });

  it("ignores malformed values instead of sending them to the API", () => {
    const params = new URLSearchParams(
      "kind=transfer&account=not-a-uuid&from=03/01/2026&page=-4&category=%27%3B--",
    );
    expect(filtersFromParams(params)).toEqual(EMPTY_FILTERS);
  });

  it("knows whether any filter is active", () => {
    expect(hasActiveFilters(EMPTY_FILTERS)).toBe(false);
    expect(hasActiveFilters({ ...EMPTY_FILTERS, page: 4 })).toBe(false);
    expect(hasActiveFilters({ ...EMPTY_FILTERS, kind: "income" })).toBe(true);
  });

  it("builds API query parameters without empty values", () => {
    expect(filtersToQuery({ ...EMPTY_FILTERS, q: "acme" })).toEqual({
      q: "acme",
      kind: undefined,
      account_id: undefined,
      category_id: undefined,
      date_from: undefined,
      date_to: undefined,
      page: 1,
    });
  });

  it("uses the local calendar date for today", () => {
    expect(todayIso(new Date(2026, 0, 5, 23, 30))).toBe("2026-01-05");
  });
});
