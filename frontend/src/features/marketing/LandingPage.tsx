import {
  ArrowRight,
  BadgeCheck,
  Building2,
  Calculator,
  ChartColumnBig,
  ChartLine,
  FileText,
  KeyRound,
  MessageSquareText,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Users,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";

import { PublicFooter } from "../../components/layout/PublicFooter";
import { PublicHeader } from "../../components/layout/PublicHeader";
import { Badge } from "../../components/ui/Badge";
import { buttonClasses } from "../../components/ui/button-styles";
import { HeroPreview } from "./HeroPreview";

type Item = { Icon: LucideIcon; title: string; text: string };

const FEATURES: Item[] = [
  {
    Icon: Wallet,
    title: "Cash flow monitoring",
    text: "See money in and out by day, week or month, and spot shortfalls before they happen.",
  },
  {
    Icon: ChartColumnBig,
    title: "Profit & loss analysis",
    text: "Automatic P&L by category and period, aligned to your own fiscal year.",
  },
  {
    Icon: Sparkles,
    title: "AI insights",
    text: "Plain-language explanations of trends and anomalies, grounded in your actual figures.",
  },
  {
    Icon: ChartLine,
    title: "Cash flow forecasting",
    text: "Statistical projections with clearly stated assumptions, never presented as certainties.",
  },
  {
    Icon: FileText,
    title: "Financial reports",
    text: "Export clear PDF and CSV reports for clients, boards and lenders.",
  },
  {
    Icon: Users,
    title: "Team & client access",
    text: "Share a workspace with owner, admin, analyst and viewer roles.",
  },
];

const AI_STEPS: Item[] = [
  {
    Icon: Calculator,
    title: "1. Calculate",
    text: "Every figure is computed with exact decimal arithmetic, never estimated by the AI.",
  },
  {
    Icon: MessageSquareText,
    title: "2. Explain",
    text: "The AI describes what the calculated results mean, in plain language.",
  },
  {
    Icon: BadgeCheck,
    title: "3. Verify",
    text: "Numbers in AI text are checked against the calculations before you ever see them.",
  },
];

const SECURITY: Item[] = [
  {
    Icon: KeyRound,
    title: "Strong password protection",
    text: "Passwords are hashed with Argon2id, the current industry recommendation.",
  },
  {
    Icon: Building2,
    title: "Isolated workspaces",
    text: "Each organization's data is visible only to its own members.",
  },
  {
    Icon: ShieldCheck,
    title: "Role-based access",
    text: "Owners decide exactly who can view, analyse or change financial data.",
  },
  {
    Icon: ScrollText,
    title: "Tamper-resistant audit trail",
    text: "Sensitive actions are recorded in a log that cannot be edited or deleted.",
  },
];

function SectionHeading({
  eyebrow,
  title,
  text,
}: {
  eyebrow: string;
  title: string;
  text: string;
}) {
  return (
    <div className="mx-auto max-w-2xl text-center">
      <p className="text-sm font-medium text-brand">{eyebrow}</p>
      <h2 className="mt-2 text-3xl font-semibold tracking-tight">{title}</h2>
      <p className="mt-3 text-muted-foreground">{text}</p>
    </div>
  );
}

function ItemGrid({ items, columns }: { items: Item[]; columns: string }) {
  return (
    <div className={`mt-12 grid gap-4 ${columns}`}>
      {items.map(({ Icon, title, text }) => (
        <div key={title} className="rounded-2xl border bg-surface p-6">
          <div className="inline-flex size-10 items-center justify-center rounded-xl bg-brand/10 text-brand">
            <Icon className="size-5" aria-hidden="true" />
          </div>
          <h3 className="mt-4 font-semibold">{title}</h3>
          <p className="mt-1.5 text-sm text-muted-foreground">{text}</p>
        </div>
      ))}
    </div>
  );
}

function Section({
  id,
  children,
  muted = false,
}: {
  id?: string;
  children: ReactNode;
  muted?: boolean;
}) {
  return (
    <section
      id={id}
      className={muted ? "scroll-mt-16 border-y bg-surface-muted/50" : "scroll-mt-16"}
    >
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">{children}</div>
    </section>
  );
}

export function LandingPage() {
  return (
    <>
      <title>Quantova Finance · AI-powered financial intelligence</title>
      <PublicHeader />

      <main id="main-content" tabIndex={-1} className="outline-none">
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 pt-16 pb-20 sm:px-6 lg:grid-cols-2 lg:pt-24">
          <div>
            <Badge tone="brand">AI-powered financial intelligence</Badge>
            <h1 className="mt-5 text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
              Understand your numbers. Act before the month closes.
            </h1>
            <p className="mt-5 max-w-xl text-lg text-muted-foreground">
              Quantova brings income, expenses, cash flow and profit & loss into one clear view,
              with AI that explains what changed and why, built on calculations you can verify.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/register" className={buttonClasses({ size: "lg" })}>
                Get started
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
              <Link to="/login" className={buttonClasses({ size: "lg", variant: "secondary" })}>
                Sign in
              </Link>
            </div>
            <p className="mt-4 text-sm text-muted-foreground">
              For businesses, financial analysts, investors and consultants.
            </p>
          </div>
          <HeroPreview />
        </section>

        <Section id="features" muted>
          <SectionHeading
            eyebrow="Features"
            title="Everything you need to understand performance"
            text="From day-to-day cash to quarterly profit, in one workspace your whole team can share."
          />
          <ItemGrid items={FEATURES} columns="sm:grid-cols-2 lg:grid-cols-3" />
        </Section>

        <Section id="ai">
          <SectionHeading
            eyebrow="How our AI works"
            title="AI you can check, not just trust"
            text="Language models are excellent at explaining and unreliable at arithmetic, so we never let them do the maths."
          />
          <ItemGrid items={AI_STEPS} columns="md:grid-cols-3" />
          <p className="mx-auto mt-8 max-w-2xl text-center text-sm text-muted-foreground">
            Insights and forecasts are estimates to support your judgement, not guarantees or
            financial advice.
          </p>
        </Section>

        <Section id="security" muted>
          <SectionHeading
            eyebrow="Security"
            title="Built for financial data from day one"
            text="Security is part of the foundation, not a feature added later."
          />
          <ItemGrid items={SECURITY} columns="sm:grid-cols-2 lg:grid-cols-4" />
        </Section>

        <Section>
          <div className="rounded-3xl border bg-surface px-6 py-14 text-center shadow-sm">
            <h2 className="text-3xl font-semibold tracking-tight">
              Ready to see your finances clearly?
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
              Create a workspace in under a minute and invite your team when you are ready.
            </p>
            <Link to="/register" className={buttonClasses({ size: "lg", className: "mt-8" })}>
              Get started
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
          </div>
        </Section>
      </main>

      <PublicFooter />
    </>
  );
}
