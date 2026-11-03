import { ArrowDownRight, ArrowUpRight, Plus } from "lucide-react";

import { Logo } from "../../components/brand/Logo";
import { ThemeToggle } from "../../components/ThemeToggle";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../../components/ui/Card";
import { Field } from "../../components/ui/Field";
import { Input } from "../../components/ui/Input";
import { ApiStatus } from "./ApiStatus";
import { cn } from "../../lib/cn";

// Illustrative figures for the design preview only.
const SAMPLE_METRICS = [
  { label: "Revenue (MTD)", value: "$482,015.00", change: "+12.4%", favorable: true },
  { label: "Operating expenses", value: "$291,540.00", change: "+3.1%", favorable: false },
  { label: "Net cash flow", value: "$190,475.00", change: "+28.9%", favorable: true },
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-12">
      <h2 className="text-sm font-medium text-muted-foreground">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export function DesignPreviewPage() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b bg-surface/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Logo />
          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <p className="text-xs font-medium tracking-[0.2em] text-muted-foreground uppercase">
          Design system preview
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
          Financial clarity, by design.
        </h1>

        <Section title="Metric cards">
          <div className="grid gap-4 sm:grid-cols-3">
            {SAMPLE_METRICS.map((metric) => (
              <Card key={metric.label} className="p-5">
                <p className="text-sm text-muted-foreground">{metric.label}</p>
                <p className="mt-2 font-mono text-2xl font-semibold tracking-tight tabular-nums">
                  {metric.value}
                </p>
                <p
                  className={cn(
                    "mt-3 inline-flex items-center gap-1 text-sm font-medium",
                    metric.favorable ? "text-positive" : "text-negative",
                  )}
                >
                  {metric.favorable ? (
                    <ArrowUpRight className="size-4" aria-hidden="true" />
                  ) : (
                    <ArrowDownRight className="size-4" aria-hidden="true" />
                  )}
                  {metric.change} vs last month
                </p>
              </Card>
            ))}
          </div>
        </Section>

        <Section title="Buttons">
          <div className="flex flex-wrap items-center gap-3">
            <Button>
              <Plus className="size-4" aria-hidden="true" />
              Add transaction
            </Button>
            <Button variant="secondary">Export CSV</Button>
            <Button variant="ghost">Cancel</Button>
            <Button variant="danger">Delete</Button>
            <Button loading>Saving</Button>
            <Button size="sm" variant="secondary">
              Small
            </Button>
            <Button size="lg">Large</Button>
          </div>
        </Section>

        <Section title="Badges">
          <div className="flex flex-wrap gap-2">
            <Badge>Draft</Badge>
            <Badge tone="brand">Owner</Badge>
            <Badge tone="positive">Paid</Badge>
            <Badge tone="negative">Overdue</Badge>
            <Badge tone="warning">Pending review</Badge>
          </div>
        </Section>

        <Section title="Form card">
          <Card className="max-w-md">
            <CardHeader>
              <CardTitle>Invite a team member</CardTitle>
              <CardDescription>They must already have a Quantova account.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              <Field label="Full name" hint="As shown on their profile.">
                {(control) => <Input placeholder="Jane Wanjiru" {...control} />}
              </Field>
              <Field label="Email" error="Enter a valid email address.">
                {(control) => (
                  <Input type="email" defaultValue="jane@" autoComplete="off" {...control} />
                )}
              </Field>
            </CardContent>
            <CardFooter className="justify-end">
              <Button variant="ghost">Cancel</Button>
              <Button type="submit">Send invite</Button>
            </CardFooter>
          </Card>
        </Section>

        <Section title="Alerts">
          <div className="grid max-w-2xl gap-3">
            <Alert tone="info" title="Forecasts are estimates">
              AI-generated projections are not guarantees of future results.
            </Alert>
            <Alert tone="success" title="Transactions imported">
              248 rows were added to March 2026.
            </Alert>
            <Alert tone="warning" title="Cash runway below 3 months">
              Review upcoming expenses in the cash flow view.
            </Alert>
            <Alert tone="error" title="Incorrect email or password" />
          </div>
        </Section>

        <Section title="Backend status">
          <div className="max-w-md">
            <ApiStatus />
          </div>
        </Section>
      </main>
    </div>
  );
}
