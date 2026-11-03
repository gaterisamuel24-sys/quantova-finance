import type { ComponentProps } from "react";

import { cn } from "../../lib/cn";
import { Spinner } from "./Spinner";
import { focusRing } from "./styles";

const VARIANTS = {
  primary: "bg-brand text-brand-foreground shadow-sm hover:bg-brand/90",
  secondary: "border bg-surface text-foreground shadow-sm hover:bg-surface-muted",
  ghost: "text-foreground hover:bg-surface-muted",
  danger: "bg-negative text-white shadow-sm hover:bg-negative/90",
} as const;

const SIZES = {
  sm: "h-8 gap-1.5 px-3 text-sm",
  md: "h-10 gap-2 px-4 text-sm",
  lg: "h-11 gap-2 px-5 text-base",
} as const;

export type ButtonProps = ComponentProps<"button"> & {
  variant?: keyof typeof VARIANTS;
  size?: keyof typeof SIZES;
  /** Shows a spinner, disables the button and marks it busy for assistive technology. */
  loading?: boolean;
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  type = "button",
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        "inline-flex items-center justify-center rounded-lg font-medium whitespace-nowrap",
        "transition-colors disabled:pointer-events-none disabled:opacity-50",
        focusRing,
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...props}
    >
      {loading && <Spinner className="size-4" label={null} />}
      {children}
    </button>
  );
}
