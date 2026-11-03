import { Logo } from "../brand/Logo";

// Calculated once when the app loads, so rendering stays pure.
const CURRENT_YEAR = new Date().getFullYear();

export function PublicFooter() {
  return (
    <footer className="border-t">
      <div className="mx-auto grid max-w-6xl gap-6 px-4 py-10 text-sm sm:px-6 md:grid-cols-2">
        <div className="grid gap-3">
          <Logo />
          <p className="text-muted-foreground">
            © {CURRENT_YEAR} Quantova Finance. All rights reserved.
          </p>
        </div>
        <p className="text-muted-foreground md:text-right">
          Quantova Finance provides financial analytics for informational purposes only.
          AI-generated insights and forecasts are estimates, not guarantees or financial advice.
        </p>
      </div>
    </footer>
  );
}
