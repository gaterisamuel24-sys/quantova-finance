import { LogOut } from "lucide-react";
import { useId, useRef, useState } from "react";

import { focusRing } from "../../components/ui/styles";
import { cn } from "../../lib/cn";
import { initials } from "../../lib/initials";
import { useDismiss } from "../../lib/use-dismiss";
import { useAuth } from "../auth/auth-context";

export function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const panelId = useId();
  useDismiss(containerRef, () => setOpen(false), open);

  if (user === null) return null;

  async function handleSignOut() {
    setSigningOut(true);
    await logout();
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        aria-label="Account menu"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((current) => !current)}
        className={cn(
          "inline-flex size-9 items-center justify-center rounded-full bg-brand/10 text-sm font-semibold text-brand",
          focusRing,
        )}
      >
        {initials(user.full_name)}
      </button>

      {open && (
        <div
          id={panelId}
          className="absolute top-full right-0 z-30 mt-2 w-64 rounded-xl border bg-surface p-1 shadow-lg"
        >
          <div className="px-3 py-2">
            <p className="truncate text-sm font-medium">{user.full_name}</p>
            <p className="truncate text-xs text-muted-foreground">{user.email}</p>
          </div>
          <div className="my-1 border-t" />
          <button
            type="button"
            disabled={signingOut}
            onClick={() => void handleSignOut()}
            className={cn(
              "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors",
              "hover:bg-surface-muted disabled:opacity-50",
              focusRing,
            )}
          >
            <LogOut className="size-4" aria-hidden="true" />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
