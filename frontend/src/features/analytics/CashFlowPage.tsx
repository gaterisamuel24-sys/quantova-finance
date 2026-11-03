import { useSearchParams } from "react-router";

import {
  BalanceLine,
  ChartLegend,
  FlowTable,
  IncomeExpenseBars,
} from "../../components/charts/CashFlowCharts";
import { Alert } from "../../components/ui/Alert";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { subtractAmounts } from "../../lib/money";
import { useCurrentOrganization } from "../organizations/current-organization";
import { useCashFlow } from "./api";
import { GranularitySelect, PeriodSelect } from "./PeriodSelect";
import { formatRange, parseGranularity, parsePeriod } from "./periods";
import { StatTile, toFlowPoints } from "./StatTile";

export function CashFlowPage() {
  const organization = useCurrentOrganization();
  const currency = organization.base_currency;
  const [searchParams, setSearchParams] = useSearchParams();
  const period = parsePeriod(searchParams.get("period"), "last_12_months");
  const granularity = parseGranularity(searchParams.get("granularity"), "month");
  const cashFlow = useCashFlow(organization.id, period, granularity);
  const points = cashFlow.data ? toFlowPoints(cashFlow.data) : [];

  function update(name: "period" | "granularity", value: string) {
    const next = new URLSearchParams(searchParams);
    next.set(name, value);
    setSearchParams(next);
  }

  return (
    <>
      <title>{`Cash flow · ${organization.name} · Quantova Finance`}</title>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Cash flow</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {cashFlow.data
              ? formatRange(cashFlow.data.period.start, cashFlow.data.period.end)
              : "Money in, money out and the cash left over."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <PeriodSelect value={period} onChange={(value) => update("period", value)} />
          <GranularitySelect
            value={granularity}
            onChange={(value) => update("granularity", value)}
          />
        </div>
      </div>

      {cashFlow.isError ? (
        <Alert tone="error" title={cashFlow.error.message} className="mt-6" />
      ) : !cashFlow.data ? (
        <div className="flex justify-center py-16">
          <Spinner label="Loading cash flow" />
        </div>
      ) : (
        <>
          <section className="mt-6 grid gap-4 sm:grid-cols-3" aria-label="Balances">
            <StatTile
              label="Opening balance"
              amount={cashFlow.data.opening_balance}
              currency={currency}
            />
            <StatTile
              label="Closing balance"
              amount={cashFlow.data.closing_balance}
              currency={currency}
            />
            <StatTile
              label="Net change"
              amount={subtractAmounts(cashFlow.data.closing_balance, cashFlow.data.opening_balance)}
              currency={currency}
            />
          </section>

          <div className="mt-6 grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Income and expenses</CardTitle>
                <CardDescription>Money in and out in each period</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-3">
                <ChartLegend
                  items={[
                    { label: "Income", swatch: "bg-chart-income" },
                    { label: "Expenses", swatch: "bg-chart-expense" },
                  ]}
                />
                <IncomeExpenseBars points={points} currency={currency} busy={cashFlow.isFetching} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Cash balance</CardTitle>
                <CardDescription>Cash at the end of each period</CardDescription>
              </CardHeader>
              <CardContent>
                <BalanceLine points={points} currency={currency} busy={cashFlow.isFetching} />
              </CardContent>
            </Card>
          </div>

          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Figures</CardTitle>
              <CardDescription>The numbers behind the charts</CardDescription>
            </CardHeader>
            <CardContent>
              <FlowTable points={points} currency={currency} caption="Cash flow by period" />
            </CardContent>
          </Card>
        </>
      )}
    </>
  );
}
