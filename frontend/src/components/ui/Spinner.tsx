import { cn } from "../../lib/cn";

type SpinnerProps = {
  className?: string;
  /** Announced to screen readers. Pass null when the surrounding element already says "busy". */
  label?: string | null;
};

export function Spinner({ className, label = "Loading" }: SpinnerProps) {
  const a11y = label === null ? { "aria-hidden": true } : { role: "status", "aria-label": label };
  return (
    <svg viewBox="0 0 24 24" className={cn("size-5 animate-spin", className)} {...a11y}>
      <circle
        cx="12"
        cy="12"
        r="9"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        className="opacity-25"
      />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}
