// Transaction list filters live in the URL (?kind=expense&page=2), so a filtered view
// survives a reload, works with the back button and can be shared as a link.

export type EntryKind = "income" | "expense";

export type TransactionFilters = {
  q: string;
  kind: EntryKind | "";
  accountId: string;
  categoryId: string;
  dateFrom: string;
  dateTo: string;
  page: number;
};

export const EMPTY_FILTERS: TransactionFilters = {
  q: "",
  kind: "",
  accountId: "",
  categoryId: "",
  dateFrom: "",
  dateTo: "",
  page: 1,
};

const PARAM_NAMES = {
  q: "q",
  kind: "kind",
  accountId: "account",
  categoryId: "category",
  dateFrom: "from",
  dateTo: "to",
} as const;

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Read filters from the URL, ignoring anything malformed rather than sending it to the API. */
export function filtersFromParams(params: URLSearchParams): TransactionFilters {
  const text = (name: string) => params.get(name)?.trim() ?? "";
  const matching = (name: string, pattern: RegExp) => {
    const value = text(name);
    return pattern.test(value) ? value : "";
  };
  const kind = text(PARAM_NAMES.kind);
  const page = Number.parseInt(text("page"), 10);

  return {
    q: text(PARAM_NAMES.q).slice(0, 100),
    kind: kind === "income" || kind === "expense" ? kind : "",
    accountId: matching(PARAM_NAMES.accountId, UUID),
    categoryId: matching(PARAM_NAMES.categoryId, UUID),
    dateFrom: matching(PARAM_NAMES.dateFrom, ISO_DATE),
    dateTo: matching(PARAM_NAMES.dateTo, ISO_DATE),
    page: Number.isInteger(page) && page > 1 ? page : 1,
  };
}

/** Write filters to URL parameters, leaving out empty ones to keep links short. */
export function filtersToParams(filters: TransactionFilters): URLSearchParams {
  const params = new URLSearchParams();
  for (const [key, name] of Object.entries(PARAM_NAMES) as [keyof typeof PARAM_NAMES, string][]) {
    const value = filters[key];
    if (value) params.set(name, value);
  }
  if (filters.page > 1) params.set("page", String(filters.page));
  return params;
}

/** Whether any filter (other than the page number) is active. */
export function hasActiveFilters(filters: TransactionFilters): boolean {
  return Object.keys(PARAM_NAMES).some((key) => filters[key as keyof typeof PARAM_NAMES] !== "");
}

/** The query parameters the API expects. Empty filters are left out. */
export function filtersToQuery(filters: TransactionFilters) {
  return {
    q: filters.q || undefined,
    kind: filters.kind || undefined,
    account_id: filters.accountId || undefined,
    category_id: filters.categoryId || undefined,
    date_from: filters.dateFrom || undefined,
    date_to: filters.dateTo || undefined,
    page: filters.page,
  };
}

/** Today's date in the user's own time zone, as YYYY-MM-DD. */
export function todayIso(now: Date = new Date()): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}
