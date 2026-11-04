import type { ReactNode } from "react";
import { Link } from "react-router";

import { PublicFooter } from "../../components/layout/PublicFooter";
import { PublicHeader } from "../../components/layout/PublicHeader";
import { buttonClasses } from "../../components/ui/button-styles";

/** A label exactly as it appears on a button or in the menu. */
function Ui({ children }: { children: ReactNode }) {
  return (
    <span className="rounded bg-brand/10 px-1.5 py-0.5 font-medium whitespace-nowrap text-foreground">
      {children}
    </span>
  );
}

type Step = { title: string; body: ReactNode };

const STEPS: Step[] = [
  {
    title: "Create your account",
    body: (
      <>
        <p>
          Choose <Ui>Get started</Ui>, then enter your name, email address and a strong password,
          and choose <Ui>Create account</Ui>.
        </p>
        <p>
          You stay signed in on that device. Use <Ui>Sign out</Ui> in the menu under your name on a
          shared computer. After several wrong passwords in a row, sign-in pauses for a short while.
        </p>
      </>
    ),
  },
  {
    title: "Set up your business",
    body: (
      <>
        <p>
          Quantova calls each business an <strong>organization</strong>. Enter its name, its{" "}
          <strong>base currency</strong> and the month your financial year starts, then choose{" "}
          <Ui>Create organization</Ui>. You become its Owner.
        </p>
        <p>
          A new organization starts with a <strong>Main account</strong> and a ready-made list of
          categories (sales, rent, salaries, utilities and more), so you can record straight away.
        </p>
      </>
    ),
  },
  {
    title: "Record money in and out",
    body: (
      <>
        <p>
          Open <Ui>Transactions</Ui>. Add one record with <Ui>Add transaction</Ui>, or many at once
          with <Ui>Import CSV</Ui>: download the template, fill it in, upload it and choose{" "}
          <Ui>Check file</Ui>. Quantova lists any rows with problems and saves nothing until every
          row is correct. Then it saves them all together.
        </p>
        <p>
          You can filter by date, type, account or category, and edit or delete any record. Every
          change is kept in the activity log. Amounts in another currency are stored and counted
          separately, so they never distort your totals.
        </p>
      </>
    ),
  },
  {
    title: "See how the business is doing",
    body: (
      <ul className="grid list-disc gap-1.5 pl-5">
        <li>
          <Ui>Overview</Ui>: money in, money out and profit for the period, compared with the period
          before, plus a twelve-month chart and your largest expenses.
        </li>
        <li>
          <Ui>Cash flow</Ui>: money in and out by day, week or month, and your cash balance over
          time.
        </li>
        <li>
          <Ui>Profit &amp; loss</Ui>: income and expenses by category, ending with net profit.
        </li>
        <li>
          Each page has a period picker: this month, last quarter, last 12 months, your financial
          year, or exact dates.
        </li>
      </ul>
    ),
  },
  {
    title: "Download reports",
    body: (
      <p>
        Use <Ui>Export transactions</Ui> on the Transactions page, or the download buttons on Cash
        flow and Profit &amp; loss, to get a <strong>CSV</strong> file for Excel or Google Sheets,
        or a <strong>PDF</strong> to send to your accountant. Each download is recorded in the
        activity log.
      </p>
    ),
  },
  {
    title: "Get an AI explanation",
    body: (
      <>
        <p>
          Open <Ui>AI insights</Ui>, pick a period and choose <Ui>Generate insights</Ui>. You get a
          few short observations and suggestions, with the figures each one is based on listed
          underneath so you can check them.
        </p>
        <p>
          Only totals are sent to the AI: no descriptions, customer or supplier names, or individual
          records. If the AI mentions a number that isn&apos;t in your figures, the answer is thrown
          away. Insights are estimates to help you think, never financial advice or a guaranteed
          outcome.
        </p>
      </>
    ),
  },
  {
    title: "Choose a plan (optional)",
    body: (
      <p>
        Everyone starts on Free. The Owner can upgrade on the <Ui>Billing</Ui> page. Payment happens
        on Stripe&apos;s secure page, so Quantova never sees your card number.{" "}
        <Ui>Manage billing</Ui> lets you change card, switch plan or cancel.
      </p>
    ),
  },
];

const PLANS = [
  { name: "Free", price: "$0", members: "1", insights: "3" },
  { name: "Pro", price: "$19", members: "up to 5", insights: "20" },
  { name: "Business", price: "$49", members: "up to 25", insights: "100" },
];

const ROLE_NAMES = ["Viewer", "Analyst", "Admin", "Owner"] as const;
// Which roles can do each thing, in the order of ROLE_NAMES.
const PERMISSIONS: { action: string; allowed: [boolean, boolean, boolean, boolean] }[] = [
  { action: "See transactions, the overview and reports", allowed: [true, true, true, true] },
  { action: "Download CSV and PDF reports", allowed: [true, true, true, true] },
  { action: "Add, edit, delete and import transactions", allowed: [false, true, true, true] },
  { action: "Generate AI insights", allowed: [false, true, true, true] },
  { action: "Change business details and members", allowed: [false, false, true, true] },
  { action: "Upgrade, change or cancel the plan", allowed: [false, false, false, true] },
];

const TERMS = [
  ["Income", "Money that comes into the business: sales, fees, interest."],
  ["Expense", "Money the business spends: rent, salaries, stock, software."],
  [
    "Profit & loss (P&L)",
    "Income minus expenses for a period. Positive is a profit, negative a loss.",
  ],
  ["Net profit", "What is left after all expenses are taken away from all income."],
  ["Cash flow", "How money moved in and out over time, and what that did to your balance."],
  ["Category", "A label that groups similar records, such as Rent or Sales."],
  ["Account", "Where the money sits, such as a bank account or an M-Pesa till."],
  ["Financial year", "The twelve months you report on. Quarters follow the start month you chose."],
];

const QUESTIONS = [
  {
    q: "Can other businesses see my data?",
    a: "No. Every page checks that you belong to the business before showing anything, and someone outside it is told the business doesn't exist. Connections are encrypted, passwords are stored in a form that can't be read back, and edits, imports and downloads are logged.",
  },
  {
    q: "Does Quantova hold or move my money?",
    a: "No. Quantova is record-keeping and analysis software. It isn't a bank, doesn't hold deposits or lend money, and can't make payments from your accounts. The only payment it handles is your own subscription, through Stripe.",
  },
  {
    q: "My import was rejected. What do I do?",
    a: "Quantova lists each problem row with the reason, such as a missing date or an amount with too many decimal places. Fix those rows and upload the file again. Nothing from the first attempt was saved, so you won't get duplicates.",
  },
  {
    q: "Why can't I add transactions?",
    a: "You are probably a Viewer in that business. Ask the Owner or an Admin to make you an Analyst.",
  },
  {
    q: "Something went wrong. What should I send?",
    a: "Error messages include a short reference code. Send that code to your administrator. It lets them find exactly what happened without needing your password or data.",
  },
];

export function GuidePage() {
  return (
    <>
      <title>How to use Quantova · Quantova Finance</title>
      <PublicHeader />
      <main
        id="main-content"
        tabIndex={-1}
        className="mx-auto grid max-w-3xl gap-14 px-4 py-12 outline-none sm:px-6"
      >
        <header className="grid gap-4">
          <p className="font-mono text-xs tracking-widest text-brand uppercase">Guide</p>
          <h1 className="text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
            How to use Quantova Finance
          </h1>
          <p className="text-lg text-muted-foreground">
            Quantova helps a small business keep track of the money coming in and going out, see
            whether it is making a profit, and get a plain-language explanation of what changed.
            This guide walks through it, page by page.
          </p>
        </header>

        <section aria-labelledby="steps" className="grid gap-6">
          <h2 id="steps" className="text-2xl font-semibold tracking-tight">
            Getting started
          </h2>
          <ol className="grid gap-0">
            {STEPS.map((step, index) => (
              <li key={step.title} className="grid grid-cols-[2.5rem_1fr] gap-4">
                <div className="flex flex-col items-center">
                  <span
                    aria-hidden="true"
                    className="grid size-8 place-items-center rounded-full bg-brand text-sm font-semibold text-brand-foreground"
                  >
                    {index + 1}
                  </span>
                  {index < STEPS.length - 1 && <span className="mt-1 w-px flex-1 bg-border" />}
                </div>
                <div className="grid min-w-0 gap-2 pb-8 text-muted-foreground">
                  <h3 className="pt-1 font-semibold text-foreground">{step.title}</h3>
                  {step.body}
                </div>
              </li>
            ))}
          </ol>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[28rem] text-sm">
              <caption className="pb-2 text-left font-medium">
                Plans (per business, monthly)
              </caption>
              <thead className="text-left text-xs text-muted-foreground uppercase">
                <tr className="border-b">
                  <th className="py-2 pr-3 font-medium">Plan</th>
                  <th className="py-2 pr-3 font-medium">Price</th>
                  <th className="py-2 pr-3 font-medium">People</th>
                  <th className="py-2 font-medium">AI insights a day</th>
                </tr>
              </thead>
              <tbody className="tabular-nums">
                {PLANS.map((plan) => (
                  <tr key={plan.name} className="border-b">
                    <td className="py-2 pr-3 font-medium">{plan.name}</td>
                    <td className="py-2 pr-3">{plan.price}</td>
                    <td className="py-2 pr-3">{plan.members}</td>
                    <td className="py-2">{plan.insights}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section aria-labelledby="roles" className="grid gap-4">
          <h2 id="roles" className="text-2xl font-semibold tracking-tight">
            Who can do what
          </h2>
          <p className="text-muted-foreground">
            Everyone in a business has a role. Give people the lowest role they need: an accountant
            who only reads reports can be a Viewer.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[34rem] text-sm">
              <thead className="text-left text-xs text-muted-foreground uppercase">
                <tr className="border-b">
                  <th className="py-2 pr-3 font-medium">What</th>
                  {ROLE_NAMES.map((role) => (
                    <th key={role} className="py-2 pr-3 font-medium">
                      {role}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {PERMISSIONS.map(({ action, allowed }) => (
                  <tr key={action} className="border-b">
                    <td className="py-2 pr-3">{action}</td>
                    {allowed.map((yes, index) => (
                      <td
                        key={ROLE_NAMES[index]}
                        className={
                          yes
                            ? "py-2 pr-3 font-medium text-positive"
                            : "py-2 pr-3 text-muted-foreground"
                        }
                      >
                        {yes ? "Yes" : "No"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section aria-labelledby="terms" className="grid gap-4">
          <h2 id="terms" className="text-2xl font-semibold tracking-tight">
            Words you&apos;ll see
          </h2>
          <dl className="grid gap-x-8 sm:grid-cols-2">
            {TERMS.map(([term, meaning]) => (
              <div key={term} className="grid gap-1 border-b py-3">
                <dt className="font-medium">{term}</dt>
                <dd className="text-sm text-muted-foreground">{meaning}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section aria-labelledby="questions" className="grid gap-4">
          <h2 id="questions" className="text-2xl font-semibold tracking-tight">
            Common questions
          </h2>
          <div className="border-t">
            {QUESTIONS.map(({ q, a }) => (
              <details key={q} className="group border-b py-3">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 rounded font-medium">
                  {q}
                  <span aria-hidden="true" className="font-mono text-brand group-open:rotate-45">
                    +
                  </span>
                </summary>
                <p className="mt-2 text-muted-foreground">{a}</p>
              </details>
            ))}
          </div>
        </section>

        <div className="flex flex-wrap gap-3">
          <Link to="/register" className={buttonClasses()}>
            Get started
          </Link>
          <Link to="/login" className={buttonClasses({ variant: "ghost" })}>
            Sign in
          </Link>
        </div>
      </main>
      <PublicFooter />
    </>
  );
}
