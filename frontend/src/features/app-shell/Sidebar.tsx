import {
  ArrowLeftRight,
  FileText,
  LayoutDashboard,
  Settings,
  Sparkles,
  Users,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { Link, NavLink } from "react-router";

import { Logo } from "../../components/brand/Logo";
import { Badge } from "../../components/ui/Badge";
import { focusRing } from "../../components/ui/styles";
import { cn } from "../../lib/cn";
import type { Organization } from "../organizations/api";
import { OrgSwitcher } from "./OrgSwitcher";

type NavItem = { label: string; Icon: LucideIcon; path?: string };

// Items without a path are coming in later phases and render as disabled.
const NAV_ITEMS: NavItem[] = [
  { label: "Overview", Icon: LayoutDashboard, path: "" },
  { label: "Transactions", Icon: ArrowLeftRight, path: "transactions" },
  { label: "Cash flow", Icon: Wallet },
  { label: "Reports", Icon: FileText },
  { label: "AI insights", Icon: Sparkles },
  { label: "Members", Icon: Users },
  { label: "Settings", Icon: Settings },
];

type SidebarProps = {
  organization: Organization;
  organizations: Organization[];
  onNavigate?: () => void;
};

export function Sidebar({ organization, organizations, onNavigate }: SidebarProps) {
  const base = `/app/${organization.id}`;
  const itemClasses = "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors";

  return (
    <aside className="flex h-full flex-col gap-6 border-r bg-surface p-4">
      <Link to="/app" className={cn("w-fit rounded-lg", focusRing)} aria-label="Quantova Finance">
        <Logo />
      </Link>

      <OrgSwitcher current={organization} organizations={organizations} onNavigate={onNavigate} />

      <nav aria-label="Workspace" className="grid gap-1">
        {NAV_ITEMS.map(({ label, Icon, path }) =>
          path === undefined ? (
            <span
              key={label}
              aria-disabled="true"
              className={cn(itemClasses, "cursor-not-allowed text-muted-foreground/70")}
            >
              <Icon className="size-4" aria-hidden="true" />
              <span className="flex-1">{label}</span>
              <Badge className="text-[10px]">Soon</Badge>
            </span>
          ) : (
            <NavLink
              key={label}
              to={path ? `${base}/${path}` : base}
              end
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  itemClasses,
                  focusRing,
                  isActive
                    ? "bg-brand/10 font-medium text-brand"
                    : "text-muted-foreground hover:bg-surface-muted hover:text-foreground",
                )
              }
            >
              <Icon className="size-4" aria-hidden="true" />
              {label}
            </NavLink>
          ),
        )}
      </nav>

      <p className="mt-auto rounded-xl border bg-surface-muted/60 p-3 text-xs text-muted-foreground">
        Insights and forecasts are estimates, not financial advice.
      </p>
    </aside>
  );
}
