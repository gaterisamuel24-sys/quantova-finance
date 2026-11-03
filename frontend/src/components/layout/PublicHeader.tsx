import { Link } from "react-router";

import { useAuth } from "../../features/auth/auth-context";
import { cn } from "../../lib/cn";
import { Logo } from "../brand/Logo";
import { ThemeToggle } from "../ThemeToggle";
import { buttonClasses } from "../ui/button-styles";
import { focusRing } from "../ui/styles";

const SECTIONS = [
  { href: "/#features", label: "Features" },
  { href: "/#ai", label: "How our AI works" },
  { href: "/#security", label: "Security" },
];

export function PublicHeader() {
  const { status } = useAuth();

  return (
    <header className="sticky top-0 z-20 border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link to="/" aria-label="Quantova Finance home" className={cn("rounded-lg", focusRing)}>
          <Logo />
        </Link>

        <nav aria-label="Main" className="hidden items-center gap-6 text-sm md:flex">
          {SECTIONS.map((section) => (
            <a
              key={section.href}
              href={section.href}
              className={cn(
                "rounded text-muted-foreground transition-colors hover:text-foreground",
                focusRing,
              )}
            >
              {section.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          {status === "authenticated" ? (
            <Link to="/app" className={buttonClasses({ size: "sm" })}>
              Go to dashboard
            </Link>
          ) : (
            <>
              <Link
                to="/login"
                className={buttonClasses({
                  variant: "ghost",
                  size: "sm",
                  className: "hidden sm:inline-flex",
                })}
              >
                Sign in
              </Link>
              <Link to="/register" className={buttonClasses({ size: "sm" })}>
                Get started
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
