import { Menu } from "lucide-react";

import { ThemeToggle } from "../../components/ThemeToggle";
import { Button } from "../../components/ui/Button";
import { UserMenu } from "./UserMenu";

export function TopBar({ title, onOpenNav }: { title: string; onOpenNav: () => void }) {
  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b bg-background/80 px-4 backdrop-blur sm:px-6 lg:px-8">
      <Button
        variant="ghost"
        size="sm"
        aria-label="Open navigation"
        onClick={onOpenNav}
        className="-ml-2 px-2 lg:hidden"
      >
        <Menu className="size-5" aria-hidden="true" />
      </Button>
      <p className="text-sm font-medium">{title}</p>
      <div className="ml-auto flex items-center gap-2">
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  );
}
