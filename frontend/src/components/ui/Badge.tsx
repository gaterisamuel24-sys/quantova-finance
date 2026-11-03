import type { ComponentProps } from "react";

import { cn } from "../../lib/cn";

const TONES = {
  neutral: "bg-surface-muted text-muted-foreground",
  brand: "bg-brand/10 text-brand",
  positive: "bg-positive/10 text-positive",
  negative: "bg-negative/10 text-negative",
  warning: "bg-warning/20 text-foreground",
} as const;

export type BadgeProps = ComponentProps<"span"> & { tone?: keyof typeof TONES };

export function Badge({ tone = "neutral", className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        TONES[tone],
        className,
      )}
      {...props}
    />
  );
}
