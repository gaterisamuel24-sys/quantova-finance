import type { FlowPoint } from "../../components/charts/CashFlowCharts";
import type { CashFlow } from "./api";
import { axisLabel, bucketLabel } from "./periods";

/** Turn a cash-flow response into chart points. */
export function toFlowPoints(cashFlow: CashFlow): FlowPoint[] {
  return cashFlow.points.map((point) => ({
    key: point.start,
    label: bucketLabel(point.start, cashFlow.granularity),
    axisLabel: axisLabel(point.start, cashFlow.granularity),
    income: point.income,
    expenses: point.expenses,
    net: point.net,
    closingBalance: point.closing_balance,
  }));
}
