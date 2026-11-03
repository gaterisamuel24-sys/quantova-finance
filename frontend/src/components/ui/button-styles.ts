import { cn } from "../../lib/cn";
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

export type ButtonVariant = keyof typeof VARIANTS;
export type ButtonSize = keyof typeof SIZES;

/** Button classes, usable on <button> and on links styled as buttons. */
export function buttonClasses({
  variant = "primary",
  size = "md",
  className,
}: { variant?: ButtonVariant; size?: ButtonSize; className?: string } = {}): string {
  return cn(
    "inline-flex items-center justify-center rounded-lg font-medium whitespace-nowrap",
    "transition-colors disabled:pointer-events-none disabled:opacity-50",
    focusRing,
    VARIANTS[variant],
    SIZES[size],
    className,
  );
}
