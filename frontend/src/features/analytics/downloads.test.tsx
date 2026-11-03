import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { filenameFromDisposition } from "../../lib/api/download";
import { createFakeBackend, makeOrganization } from "../../test/fake-backend";
import { renderRoute } from "../../test/render";

// jsdom cannot save files, so record what the app asks the browser to download instead.
let saved: string[] = [];

beforeEach(() => {
  saved = [];
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    saved.push(this.download);
  });
  Object.defineProperty(URL, "createObjectURL", {
    configurable: true,
    writable: true,
    value: vi.fn(() => "blob:report"),
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    configurable: true,
    writable: true,
    value: vi.fn(),
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

function open(page: string) {
  const organization = makeOrganization("Acme Ltd", "KES");
  const view = renderRoute(
    `/app/${organization.id}${page}`,
    createFakeBackend({ signedIn: true, organizations: [organization] }),
  );
  /** The URL of the most recent report request. */
  const reportUrl = () => {
    const urls = view.fetchMock.mock.calls
      .map(([input]) => (input instanceof Request ? input.url : String(input)))
      .filter((url) => url.includes("/reports/"));
    return new URL(urls[urls.length - 1]);
  };
  return { ...view, reportUrl };
}

describe("report downloads", () => {
  it("downloads profit & loss as PDF for the chosen period", async () => {
    const { reportUrl } = open("/profit-loss?period=last_quarter");

    fireEvent.click(await screen.findByRole("button", { name: "Download profit & loss as PDF" }));

    await waitFor(() => expect(saved).toEqual(["acme-ltd-profit-loss.pdf"]));
    expect(reportUrl().pathname).toMatch(/\/reports\/profit-loss\.pdf$/);
    expect(reportUrl().searchParams.get("period")).toBe("last_quarter");
  });

  it("downloads cash flow as CSV with the chosen grouping", async () => {
    const { reportUrl } = open("/cash-flow?granularity=week");

    fireEvent.click(await screen.findByRole("button", { name: "Download cash flow as CSV" }));

    await waitFor(() => expect(saved).toEqual(["acme-ltd-cash-flow.csv"]));
    expect(reportUrl().searchParams.get("granularity")).toBe("week");
    expect(reportUrl().searchParams.get("period")).toBe("last_12_months");
  });

  it("exports transactions for a period and type", async () => {
    const { reportUrl } = open("/transactions");

    fireEvent.click(await screen.findByRole("button", { name: "Export CSV" }));
    const dialog = within(await screen.findByRole("dialog", { name: "Export transactions" }));
    fireEvent.change(dialog.getByLabelText("Include"), { target: { value: "expense" } });
    fireEvent.click(dialog.getByRole("button", { name: "Download CSV" }));

    await waitFor(() => expect(saved).toEqual(["acme-ltd-transactions.csv"]));
    expect(reportUrl().searchParams.get("kind")).toBe("expense");
    expect(reportUrl().searchParams.get("period")).toBe("this_month");
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });
});

describe("filenameFromDisposition", () => {
  it("reads a plain file name", () => {
    expect(filenameFromDisposition('attachment; filename="acme-ltd-cash-flow.csv"')).toBe(
      "acme-ltd-cash-flow.csv",
    );
  });

  it("ignores missing headers and names containing paths", () => {
    expect(filenameFromDisposition(null)).toBeNull();
    expect(filenameFromDisposition('attachment; filename="../../evil.csv"')).toBeNull();
  });
});
