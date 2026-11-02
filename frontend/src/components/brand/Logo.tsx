export function Logo() {
  return (
    <span className="inline-flex items-center gap-2.5">
      <svg viewBox="0 0 32 32" className="size-8" aria-hidden="true">
        <rect width="32" height="32" rx="9" className="fill-brand" />
        <circle
          cx="15"
          cy="15"
          r="7"
          fill="none"
          strokeWidth="3"
          className="stroke-brand-foreground"
        />
        <path
          d="M19.5 19.5 L24 24"
          strokeWidth="3"
          strokeLinecap="round"
          className="stroke-brand-foreground"
        />
      </svg>
      <span className="text-base font-semibold tracking-tight">
        Quantova<span className="font-normal text-muted-foreground"> Finance</span>
      </span>
    </span>
  );
}
