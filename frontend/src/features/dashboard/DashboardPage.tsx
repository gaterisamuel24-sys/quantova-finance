import { ChartColumn } from "lucide-react";
import { useState } from "react";
import { Link, useSearchParams } from "react-router";

import { ChartLegend, FlowTable, IncomeExpenseBars } from "../../components/charts/CashFlowCharts";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { buttonClasses } from "../../components/ui/button-styles";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { formatMoney } from "../../lib/money";
import { useCashFlow, useProfitLoss, useSummary, type CategorySection } from "../analytics/api";
import { PeriodSelect } from "../analytics/PeriodSelect";
import { formatRange, parsePeriod, type Period } from "../analytics/periods";
import { StatTile, toFlowPoints } from "../analytics/StatTile";
import { useAuth } from "../auth/auth-context";
import { useCurrentOrganization } from "../organizations/current-organization";

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

const DISCLAIMER =
  "Figures are calculated from the transactions recorded in Quantova. They describe the " +
  "past; they are not a forecast and not financial advice.";

const DATE = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

export function DashboardPage() {
  const organization = useCurrentOrganization();
  const { user } = useAuth();
  const firstName = user?.full_name.split(" ")[0] ?? "";
  const [searchParams, setSearchParams] = useSearchParams();
  const period = parsePeriod(searchParams.get("period"), "this_month");
  const currency = organization.base_currency;

  const summary = useSummary(organization.id, period);
  const profitLoss = useProfitLoss(organization.id, period);

  function changePeriod(next: Period) {
    setSearchParams(next === "this_month" ? {} : { period: next });
  }

  return (
    <>
      <title>{`Overview · ${organization.name} · Quantova Finance`}</title>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-muted-foreground">Welcome back, {firstName}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{organization.name}</h1>
          <div className="mt-2 flex flex-wrap gap-2">
            <Badge tone="brand" className="capitalize">
              {organization.my_role}
            </Badge>
            <Badge>{currency}</Badge>
            <Badge>FY starts {MONTHS[organization.fiscal_year_start_month - 1]}</Badge>
          </div>
        </div>
        <div className="grid gap-1 text-right">
          <PeriodSelect value={period} onChange={changePeriod} />
          {summary.data && (
            <p className="text-xs text-muted-foreground">
              {formatRange(summary.data.period.start, summary.data.period.end)}
            </p>
          )}
        </div>
      </div>

      {summary.isError && (
        <Alert tone="error" title={summary.error.message} className="mt-6">
          <Button
            variant="secondary"
            size="sm"
            className="mt-2"
            onClick={() => void summary.refetch()}
          >
            Try again
          </Button>
        </Alert>
      )}

      {summary.data && summary.data.other_currency_transaction_count > 0 && (
        <Alert tone="warning" title="Some transactions are not included" className="mt-6">
          {summary.data.other_currency_transaction_count} transactions in this period are in a
          currency other than {currency}. They are left out rather than mixed with {currency}{" "}
          amounts.
        </Alert>
      )}

      <section
        className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
        aria-label="Key figures"
        aria-busy={summary.isFetching}
      >
        {summary.data ? (
          <>
            <StatTile
              label="Income"
              amount={summary.data.current.income}
              currency={currency}
              change={{ pct: summary.data.change.income_pct, higherIsBetter: true }}
            />
            <StatTile
              label="Expenses"
              amount={summary.data.current.expenses}
              currency={currency}
              change={{ pct: summary.data.change.expenses_pct, higherIsBetter: false }}
            />
            <StatTile
              label="Net profit"
              amount={summary.data.current.net}
              currency={currency}
              change={{ pct: summary.data.change.net_pct, higherIsBetter: true }}
            />
            <StatTile
              label="Cash balance"
              amount={summary.data.cash_balance}
              currency={currency}
              footnote={`As of ${DATE.format(new Date(`${summary.data.cash_balance_as_of}T00:00:00Z`))}`}
            />
          </>
        ) : (
          !summary.isError && (
            <div className="col-span-full flex justify-center py-10">
              <Spinner label="Loading key figures" />
            </div>
          )
        )}
      </section>

      {summary.data?.current.transaction_count === 0 && (
        <Alert tone="info" title="No transactions in this period" className="mt-4">
          <Link
            to="transactions"
            className="font-medium text-brand underline-offset-4 hover:underline"
          >
            Add or import transactions
          </Link>{" "}
          to see your figures here.
        </Alert>
      )}

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <CashFlowCard orgId={organization.id} currency={currency} />

        <Card>
          <CardHeader>
            <CardTitle>Top expenses</CardTitle>
            <CardDescription>Where money went in this period</CardDescription>
          </CardHeader>
          <CardContent>
            {profitLoss.data ? (
              <TopExpenses section={profitLoss.data.expenses} currency={currency} />
            ) : profitLoss.isError ? (
              <Alert tone="error" title={profitLoss.error.message} />
            ) : (
              <Spinner label="Loading expenses" />
            )}
          </CardContent>
        </Card>
      </div>

      <p className="mt-6 text-xs text-muted-foreground">{DISCLAIMER}</p>
    </>
  );
}

const isZero = (amount: string) => /^-?0(\.0+)?$/.test(amount);

/** Always the last 12 months, by month: the long view, whatever period is selected above. */
function CashFlowCard({ orgId, currency }: { orgId: string; currency: string }) {
  const cashFlow = useCashFlow(orgId, "last_12_months", "month");
  const [showTable, setShowTable] = useState(false);
  const points = cashFlow.data ? toFlowPoints(cashFlow.data) : [];
  const empty = points.every((point) => isZero(point.income) && isZero(point.expenses));

  return (
    <Card className="lg:col-span-2">
      <CardHeader className="flex-row flex-wrap items-start justify-between gap-3">
        <div className="grid gap-1">
          <CardTitle>Cash flow</CardTitle>
          <CardDescription>Income and expenses, last 12 months</CardDescription>
        </div>
        <Link to="cash-flow" className={buttonClasses({ variant: "ghost", size: "sm" })}>
          Details
        </Link>
      </CardHeader>
      <CardContent className="grid gap-4">
        {cashFlow.isError ? (
          <Alert tone="error" title={cashFlow.error.message} />
        ) : !cashFlow.data ? (
          <div className="flex h-56 items-center justify-center">
            <Spinner label="Loading cash flow" />
          </div>
        ) : empty ? (
          <div className="flex h-56 flex-col items-center justify-center gap-3 rounded-xl border border-dashed text-center">
            <ChartColumn className="size-6 text-muted-foreground" aria-hidden="true" />
            <p className="max-w-xs text-sm text-muted-foreground">
              Your cash flow chart appears here once you add transactions.
            </p>
          </div>
        ) : (
          <>
            <ChartLegend
              items={[
                { label: "Income", swatch: "bg-chart-income" },
                { label: "Expenses", swatch: "bg-chart-expense" },
              ]}
            />
            <IncomeExpenseBars points={points} currency={currency} busy={cashFlow.isFetching} />
            <Button
              variant="ghost"
              size="sm"
              className="w-fit"
              aria-expanded={showTable}
              onClick={() => setShowTable((shown) => !shown)}
            >
              {showTable ? "Hide table" : "Show as table"}
            </Button>
            {showTable && (
              <FlowTable points={points} currency={currency} caption="Cash flow, last 12 months" />
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function TopExpenses({ section, currency }: { section: CategorySection; currency: string }) {
  const top = section.lines.slice(0, 5);
  if (top.length === 0) {
    return <p className="text-sm text-muted-foreground">No expenses recorded in this period.</p>;
  }
  return (
    <ul className="grid gap-4">
      {top.map((line) => (
        <li key={line.category_id ?? "uncategorized"} className="grid gap-1.5">
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="truncate">{line.name}</span>
            <span className="font-mono tabular-nums">{formatMoney(line.amount, currency)}</span>
          </div>
          <div className="h-1.5 rounded-full bg-surface-muted" aria-hidden="true">
            <div
              className="h-full rounded-full bg-chart-expense"
              style={{ width: `${line.share_pct ?? "0"}%` }}
            />
          </div>
          <p className="text-xs text-muted-foreground">{line.share_pct ?? "0"}% of expenses</p>
        </li>
      ))}
    </ul>
  );
}
