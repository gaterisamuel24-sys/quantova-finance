import { ChevronDown } from "lucide-react";
import type { ComponentProps } from "react";

import { cn } from "../../lib/cn";
import { focusRing } from "./styles";

/** A styled native <select>: fully keyboard- and screen-reader-accessible by default. */
export function Select({ className, children, ...props }: ComponentProps<"select">) {
  return (
    <div className="relative">
      <select
        className={cn(
          "h-10 w-full appearance-none rounded-lg border bg-surface pr-9 pl-3 text-sm text-foreground shadow-sm",
          "transition-colors disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-negative",
          focusRing,
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-muted-foreground"
        aria-hidden="true"
      />
    </div>
  );
}
