import { CircleCheck } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";

import { Logo } from "../../components/brand/Logo";
import { ThemeToggle } from "../../components/ThemeToggle";
import { focusRing } from "../../components/ui/styles";
import { cn } from "../../lib/cn";

const POINTS = [
  "Income, expenses and cash flow in one place",
  "AI explanations grounded in exact calculations",
  "Role-based access for your team and clients",
];

type AuthLayoutProps = {
  title: string;
  subtitle: string;
  footer?: ReactNode;
  children: ReactNode;
};

export function AuthLayout({ title, subtitle, footer, children }: AuthLayoutProps) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <aside className="hidden flex-col justify-between border-r bg-surface-muted/60 p-10 lg:flex">
        <Link
          to="/"
          aria-label="Quantova Finance home"
          className={cn("w-fit rounded-lg", focusRing)}
        >
          <Logo />
        </Link>
        <div>
          <p className="max-w-md text-3xl font-semibold tracking-tight text-balance">
            Financial clarity for teams that move fast.
          </p>
          <ul className="mt-8 grid gap-4 text-sm">
            {POINTS.map((point) => (
              <li key={point} className="flex items-center gap-3">
                <CircleCheck className="size-5 text-brand" aria-hidden="true" />
                {point}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-muted-foreground">
          Insights and forecasts are estimates, not financial advice.
        </p>
      </aside>

      <div className="flex flex-col">
        <div className="flex h-16 items-center justify-between px-4 sm:px-6">
          <Link
            to="/"
            aria-label="Quantova Finance home"
            className={cn("rounded-lg lg:invisible", focusRing)}
          >
            <Logo />
          </Link>
          <ThemeToggle />
        </div>
        <main className="flex flex-1 items-center justify-center px-4 pb-16 sm:px-6">
          <div className="w-full max-w-sm">
            <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
            <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>
            <div className="mt-8">{children}</div>
            {footer && <p className="mt-6 text-center text-sm text-muted-foreground">{footer}</p>}
          </div>
        </main>
      </div>
    </div>
  );
}
