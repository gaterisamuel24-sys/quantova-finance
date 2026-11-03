import type { ComponentProps } from "react";

import { cn } from "../../lib/cn";
import { focusRing } from "./styles";

export function Input({ className, ...props }: ComponentProps<"input">) {
  return (
    <input
      className={cn(
        "h-10 w-full rounded-lg border bg-surface px-3 text-sm text-foreground shadow-sm",
        "transition-colors placeholder:text-muted-foreground",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "aria-invalid:border-negative aria-invalid:focus-visible:outline-negative",
        focusRing,
        className,
      )}
      {...props}
    />
  );
}
