import { cn } from "../../lib/cn";
import { initials } from "../../lib/initials";

export function OrgAvatar({ name, className }: { name: string; className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "inline-flex size-8 shrink-0 items-center justify-center rounded-lg bg-brand/10 text-xs font-semibold text-brand",
        className,
      )}
    >
      {initials(name)}
    </span>
  );
}
