import { cn } from "../lib/cn";
import { focusRing } from "./ui/styles";

/** Invisible until focused with Tab; lets keyboard users jump past navigation. */
export function SkipLink() {
  return (
    <a
      href="#main-content"
      className={cn(
        "sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50",
        "focus:rounded-lg focus:bg-surface focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:shadow-lg",
        focusRing,
      )}
    >
      Skip to main content
    </a>
  );
}
