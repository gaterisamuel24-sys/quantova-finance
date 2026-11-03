import { useState } from "react";
import { useSearchParams } from "react-router";

import { Alert } from "../../components/ui/Alert";
import { Card } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { cn } from "../../lib/cn";
import { formatMoney } from "../../lib/money";
import { useCurrentOrganization } from "../organizations/current-organization";
import { useProfitLoss, type CategorySection } from "./api";
import { DownloadButton } from "./DownloadButton";
import { PeriodSelect } from "./PeriodSelect";
import { formatRange, parsePeriod, periodLabel } from "./periods";

/** A profit & loss statement: income and expenses by category, net profit and margin. */
export function ProfitLossPage() {
  const organization = useCurrentOrganization();
  const currency = organization.base_currency;
  const [searchParams, setSearchParams] = useSearchParams();
  const period = parsePeriod(searchParams.get("period"), "this_month");
  const report = useProfitLoss(organization.id, period);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const reportPath = `/api/v1/orgs/${encodeURIComponent(organization.id)}/reports`;

  return (
    <>
      <title>{`Profit & loss · ${organization.name} · Quantova Finance`}</title>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Profit &amp; loss</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {report.data
              ? `${periodLabel(period)} · ${formatRange(report.data.period.start, report.data.period.end)} · ${currency}`
              : "Income and expenses by category."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <PeriodSelect value={period} onChange={(value) => setSearchParams({ period: value })} />
          <DownloadButton
            label="CSV"
            description="Download profit & loss as CSV"
            path={`${reportPath}/profit-loss.csv`}
            query={{ period }}
            fallbackName="profit-loss.csv"
            onError={setDownloadError}
          />
          <DownloadButton
            label="PDF"
            description="Download profit & loss as PDF"
            path={`${reportPath}/profit-loss.pdf`}
            query={{ period }}
            fallbackName="profit-loss.pdf"
            onError={setDownloadError}
          />
        </div>
      </div>

      {downloadError && <Alert tone="error" title={downloadError} className="mt-4" />}

      {report.isError ? (
        <Alert tone="error" title={report.error.message} className="mt-6" />
      ) : !report.data ? (
        <div className="flex justify-center py-16">
          <Spinner label="Loading profit and loss" />
        </div>
      ) : (
        <Card
          className={cn(
            "mt-6 overflow-hidden transition-opacity",
            report.isFetching && "opacity-60",
          )}
        >
          <div className="overflow-x-auto">
            <table className="w-full min-w-[32rem] text-sm">
              <caption className="sr-only">Profit and loss statement in {currency}</caption>
              <thead className="border-b bg-surface-muted/60 text-xs text-muted-foreground">
                <tr>
                  <th scope="col" className="px-5 py-3 text-left font-medium">
                    Category
                  </th>
                  <th scope="col" className="px-5 py-3 text-right font-medium">
                    Transactions
                  </th>
                  <th scope="col" className="px-5 py-3 text-right font-medium">
                    Share
                  </th>
                  <th scope="col" className="px-5 py-3 text-right font-medium">
                    Amount
                  </th>
                </tr>
              </thead>
              <Section title="Income" section={report.data.income} currency={currency} />
              <Section title="Expenses" section={report.data.expenses} currency={currency} />
              <tbody>
                <tr className="border-t-2 bg-surface-muted/40">
                  <th
                    scope="row"
                    colSpan={3}
                    className="px-5 py-4 text-left text-base font-semibold"
                  >
                    Net profit
                  </th>
                  <td
                    className={cn(
                      "px-5 py-4 text-right font-mono text-base font-semibold tabular-nums",
                      report.data.net_profit.startsWith("-") && "text-negative",
                    )}
                  >
                    {formatMoney(report.data.net_profit, currency)}
                  </td>
                </tr>
                <tr>
                  <th
                    scope="row"
                    colSpan={3}
                    className="px-5 py-3 text-left font-normal text-muted-foreground"
                  >
                    Profit margin
                  </th>
                  <td className="px-5 py-3 text-right font-mono tabular-nums">
                    {report.data.margin_pct === null ? "—" : `${report.data.margin_pct}%`}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <p className="mt-6 text-xs text-muted-foreground">
        Based on the transactions recorded in Quantova for this period. This is a management report,
        not audited financial statements.
      </p>
    </>
  );
}

function Section({
  title,
  section,
  currency,
}: {
  title: string;
  section: CategorySection;
  currency: string;
}) {
  const amount = "px-5 py-2.5 text-right font-mono tabular-nums";
  return (
    <tbody>
      <tr>
        <th
          scope="rowgroup"
          colSpan={4}
          className="px-5 pt-5 pb-2 text-left text-xs font-semibold tracking-wide text-muted-foreground uppercase"
        >
          {title}
        </th>
      </tr>
      {section.lines.length === 0 ? (
        <tr>
          <td colSpan={4} className="px-5 py-2.5 text-muted-foreground">
            No {title.toLowerCase()} in this period
          </td>
        </tr>
      ) : (
        section.lines.map((line) => (
          <tr key={line.category_id ?? "uncategorized"}>
            <th scope="row" className="px-5 py-2.5 text-left font-normal">
              {line.name}
            </th>
            <td className="px-5 py-2.5 text-right text-muted-foreground tabular-nums">
              {line.transaction_count}
            </td>
            <td className="px-5 py-2.5 text-right text-muted-foreground tabular-nums">
              {line.share_pct === null ? "—" : `${line.share_pct}%`}
            </td>
            <td className={amount}>{formatMoney(line.amount, currency)}</td>
          </tr>
        ))
      )}
      <tr className="border-t">
        <th scope="row" colSpan={3} className="px-5 py-3 text-left font-medium">
          Total {title.toLowerCase()}
        </th>
        <td className={cn(amount, "py-3 font-semibold")}>{formatMoney(section.total, currency)}</td>
      </tr>
    </tbody>
  );
}
