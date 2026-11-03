import { ChartLine, Circle, CircleCheck } from "lucide-react";

import { Badge } from "../../components/ui/Badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/Card";
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

const METRICS = ["Revenue", "Expenses", "Net profit", "Cash balance"];

const CHECKLIST = [
  { label: "Create your organization", done: true },
  { label: "Add your first transactions", done: false },
  { label: "Invite your team", done: false },
  { label: "Generate your first AI insight", done: false },
];

export function DashboardPage() {
  const organization = useCurrentOrganization();
  const { user } = useAuth();
  const firstName = user?.full_name.split(" ")[0] ?? "";

  return (
    <>
      <title>{`Overview · ${organization.name} · Quantova Finance`}</title>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-muted-foreground">Welcome back, {firstName}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{organization.name}</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone="brand" className="capitalize">
            {organization.my_role}
          </Badge>
          <Badge>{organization.base_currency}</Badge>
          <Badge>FY starts {MONTHS[organization.fiscal_year_start_month - 1]}</Badge>
        </div>
      </div>

      <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Key metrics">
        {METRICS.map((label) => (
          <Card key={label} className="p-5">
            <p className="text-sm text-muted-foreground">
              {label} <span className="text-xs">({organization.base_currency})</span>
            </p>
            <p className="mt-2 font-mono text-2xl font-semibold text-muted-foreground tabular-nums">
              —
            </p>
            <p className="mt-3 text-xs text-muted-foreground">No data yet</p>
          </Card>
        ))}
      </section>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Cash flow</CardTitle>
            <CardDescription>Money in and out over time</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex h-56 flex-col items-center justify-center gap-3 rounded-xl border border-dashed text-center">
              <ChartLine className="size-6 text-muted-foreground" aria-hidden="true" />
              <p className="max-w-xs text-sm text-muted-foreground">
                Your cash flow chart appears here once you add transactions.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Getting started</CardTitle>
            <CardDescription>Set up your workspace</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="grid gap-3 text-sm">
              {CHECKLIST.map((item) => (
                <li key={item.label} className="flex items-center gap-3">
                  {item.done ? (
                    <CircleCheck className="size-5 text-positive" aria-hidden="true" />
                  ) : (
                    <Circle className="size-5 text-muted-foreground" aria-hidden="true" />
                  )}
                  <span className={item.done ? "text-muted-foreground line-through" : undefined}>
                    {item.label}
                  </span>
                  <span className="sr-only">{item.done ? "(done)" : "(to do)"}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
