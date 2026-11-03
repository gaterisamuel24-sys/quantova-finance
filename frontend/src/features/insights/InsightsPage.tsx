import {
  CircleAlert,
  CircleCheck,
  Info,
  Lightbulb,
  Sparkles,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";

import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Spinner } from "../../components/ui/Spinner";
import { cn } from "../../lib/cn";
import { formatMoney } from "../../lib/money";
import { PeriodSelect } from "../analytics/PeriodSelect";
import { formatRange, periodLabel, type Period } from "../analytics/periods";
import { useCurrentOrganization } from "../organizations/current-organization";
import { canEditLedger } from "../organizations/roles";
import { useGenerateInsight, useInsights, type Fact, type Insight, type Observation } from "./api";

const KIND: Record<
  Observation["kind"],
  { label: string; Icon: LucideIcon; tone: "positive" | "negative" | "neutral" | "warning" }
> = {
  positive: { label: "Positive", Icon: CircleCheck, tone: "positive" },
  negative: { label: "Negative", Icon: CircleAlert, tone: "negative" },
  neutral: { label: "Note", Icon: Info, tone: "neutral" },
  risk: { label: "Risk", Icon: TriangleAlert, tone: "warning" },
};

const GENERATED_AT = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/** A cited figure, formatted exactly from its decimal string. */
export function formatFact(fact: Fact, currency: string): string {
  switch (fact.unit) {
    case "money":
      return formatMoney(fact.value, currency);
    case "percent":
      return `${fact.value}%`;
    case "months":
      return `${fact.value} months`;
    default:
      return fact.value.replace(/\.0+$/, "");
  }
}

export function InsightsPage() {
  const organization = useCurrentOrganization();
  const canGenerate = canEditLedger(organization);
  const insights = useInsights(organization.id);
  const generate = useGenerateInsight(organization.id);
  const [period, setPeriod] = useState<Period>("this_month");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const data = insights.data;
  const selected = data?.items.find((item) => item.id === selectedId) ?? data?.items[0];

  async function handleGenerate() {
    try {
      const created = await generate.mutateAsync(period);
      setSelectedId(created.id);
    } catch {
      // The message is shown from generate.error below.
    }
  }

  return (
    <>
      <title>{`AI insights · ${organization.name} · Quantova Finance`}</title>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">AI insights</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Plain-language explanations of your figures, written by an AI model from your totals
            only. Transaction descriptions and customer or supplier names are never shared.
          </p>
        </div>
        {canGenerate && data && (
          <div className="grid justify-items-end gap-1">
            <div className="flex flex-wrap gap-2">
              <PeriodSelect value={period} onChange={setPeriod} />
              <Button
                loading={generate.isPending}
                disabled={!data.ai_enabled || data.remaining_today === 0}
                onClick={() => void handleGenerate()}
              >
                {!generate.isPending && <Sparkles className="size-4" aria-hidden="true" />}
                Generate insights
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              {data.remaining_today} of {data.daily_limit} left today
            </p>
          </div>
        )}
      </div>

      <Alert tone="info" className="mt-6" title="Estimates, not advice">
        Insights describe your recorded figures. They are not financial, tax or legal advice and do
        not predict or guarantee outcomes. Every number shown is checked against your figures, which
        are listed under each point.
      </Alert>

      {data && !data.ai_enabled && (
        <Alert tone="warning" className="mt-4" title="AI insights are switched off on this server">
          An administrator needs to configure an AI provider key before insights can be generated.
          Existing insights can still be read.
        </Alert>
      )}
      {generate.isPending && (
        <Alert tone="info" className="mt-4" title="Analysing your figures…">
          This usually takes a few seconds.
        </Alert>
      )}
      {generate.isError && <Alert tone="error" className="mt-4" title={generate.error.message} />}

      {insights.isPending ? (
        <div className="flex justify-center py-16">
          <Spinner label="Loading insights" />
        </div>
      ) : insights.isError ? (
        <Alert tone="error" className="mt-6" title={insights.error.message} />
      ) : !selected ? (
        <Card className="mt-6">
          <CardContent className="flex flex-col items-center gap-3 py-14 text-center">
            <Sparkles className="size-6 text-muted-foreground" aria-hidden="true" />
            <p className="font-medium">No insights yet</p>
            <p className="max-w-sm text-sm text-muted-foreground">
              {canGenerate
                ? "Choose a period and generate your first insights."
                : "Insights generated by your team will appear here."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,1fr)_18rem]">
          <InsightDetail insight={selected} />
          {data && data.items.length > 1 && (
            <History items={data.items} selectedId={selected.id} onSelect={setSelectedId} />
          )}
        </div>
      )}
    </>
  );
}

function FactList({ ids, insight }: { ids: string[]; insight: Insight }) {
  const facts = ids
    .map((id) => insight.facts.find((fact) => fact.id === id))
    .filter((fact): fact is Fact => fact !== undefined);
  if (facts.length === 0) return null;
  return (
    <div className="mt-3">
      <p className="text-xs font-medium text-muted-foreground">Based on</p>
      <ul className="mt-1 flex flex-wrap gap-2">
        {facts.map((fact) => (
          <li key={fact.id} className="rounded-lg border bg-surface-muted/50 px-2 py-1 text-xs">
            <span className="text-muted-foreground">{fact.label}: </span>
            <span className="font-mono font-medium tabular-nums">
              {formatFact(fact, insight.currency)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function InsightDetail({ insight }: { insight: Insight }) {
  return (
    <Card>
      <CardHeader>
        <p className="text-xs text-muted-foreground">
          {insight.period_preset ? `${periodLabel(insight.period_preset)} · ` : ""}
          {formatRange(insight.period_start, insight.period_end)} · Generated{" "}
          {GENERATED_AT.format(new Date(insight.created_at))}
        </p>
        <h2 className="text-lg font-semibold tracking-tight">{insight.headline}</h2>
      </CardHeader>
      <CardContent className="grid gap-6">
        <section aria-label="Observations" className="grid gap-4">
          {insight.observations.map((observation, index) => {
            const { label, Icon, tone } = KIND[observation.kind];
            return (
              <article key={`${observation.title}-${index}`} className="rounded-xl border p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={tone} className="gap-1">
                    <Icon className="size-3" aria-hidden="true" />
                    {label}
                  </Badge>
                  <h3 className="font-medium">{observation.title}</h3>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{observation.detail}</p>
                <FactList ids={observation.fact_ids} insight={insight} />
              </article>
            );
          })}
        </section>

        {insight.suggestions.length > 0 && (
          <section aria-labelledby={`suggestions-${insight.id}`}>
            <h3 id={`suggestions-${insight.id}`} className="flex items-center gap-2 font-semibold">
              <Lightbulb className="size-4 text-warning" aria-hidden="true" />
              Things to look into
            </h3>
            <ul className="mt-3 grid gap-3">
              {insight.suggestions.map((suggestion, index) => (
                <li
                  key={`${suggestion.title}-${index}`}
                  className="rounded-xl bg-surface-muted/50 p-4"
                >
                  <p className="font-medium">{suggestion.title}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{suggestion.detail}</p>
                  <FactList ids={suggestion.fact_ids} insight={insight} />
                </li>
              ))}
            </ul>
          </section>
        )}

        <p className="text-xs text-muted-foreground">
          Written by {insight.model}. Figures in {insight.currency}.
        </p>
      </CardContent>
    </Card>
  );
}

function History({
  items,
  selectedId,
  onSelect,
}: {
  items: Insight[];
  selectedId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <Card className="h-fit">
      <CardHeader>
        <CardTitle>Earlier insights</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="grid gap-1">
          {items.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                aria-current={item.id === selectedId ? "true" : undefined}
                onClick={() => onSelect(item.id)}
                className={cn(
                  "w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-surface-muted",
                  item.id === selectedId && "bg-brand/10",
                )}
              >
                <span className="block text-xs text-muted-foreground">
                  {formatRange(item.period_start, item.period_end)}
                </span>
                <span className="line-clamp-2">{item.headline}</span>
              </button>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
