import { Check, ChevronsUpDown, Plus } from "lucide-react";
import { useId, useRef, useState } from "react";
import { Link } from "react-router";

import { focusRing } from "../../components/ui/styles";
import { cn } from "../../lib/cn";
import { useDismiss } from "../../lib/use-dismiss";
import type { Organization } from "../organizations/api";
import { OrgAvatar } from "../organizations/OrgAvatar";

type OrgSwitcherProps = {
  current: Organization;
  organizations: Organization[];
  onNavigate?: () => void;
};

export function OrgSwitcher({ current, organizations, onNavigate }: OrgSwitcherProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const panelId = useId();
  useDismiss(containerRef, () => setOpen(false), open);

  function choose() {
    setOpen(false);
    onNavigate?.();
  }

  const itemClasses = cn(
    "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors hover:bg-surface-muted",
    focusRing,
  );

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        aria-label={`Switch organization (current: ${current.name})`}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "flex w-full items-center gap-3 rounded-xl border bg-surface p-2.5 text-left shadow-sm transition-colors hover:bg-surface-muted",
          focusRing,
        )}
      >
        <OrgAvatar name={current.name} />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium">{current.name}</span>
          <span className="block text-xs text-muted-foreground capitalize">
            {current.my_role} · {current.base_currency}
          </span>
        </span>
        <ChevronsUpDown className="size-4 text-muted-foreground" aria-hidden="true" />
      </button>

      {open && (
        <div
          id={panelId}
          className="absolute inset-x-0 top-full z-30 mt-2 rounded-xl border bg-surface p-1 shadow-lg"
        >
          <p className="px-2.5 py-1.5 text-xs font-medium text-muted-foreground">Organizations</p>
          <ul>
            {organizations.map((organization) => (
              <li key={organization.id}>
                <Link
                  to={`/app/${organization.id}`}
                  onClick={choose}
                  aria-current={organization.id === current.id ? "true" : undefined}
                  className={itemClasses}
                >
                  <OrgAvatar name={organization.name} className="size-6 rounded-md text-[10px]" />
                  <span className="flex-1 truncate">{organization.name}</span>
                  {organization.id === current.id && (
                    <Check className="size-4 text-brand" aria-hidden="true" />
                  )}
                </Link>
              </li>
            ))}
          </ul>
          <div className="my-1 border-t" />
          <Link to="/app/new" onClick={choose} className={itemClasses}>
            <Plus className="size-4" aria-hidden="true" />
            Create organization
          </Link>
        </div>
      )}
    </div>
  );
}
