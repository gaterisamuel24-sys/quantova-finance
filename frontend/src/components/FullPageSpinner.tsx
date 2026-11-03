import { Spinner } from "./ui/Spinner";

export function FullPageSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center text-muted-foreground">
      <Spinner className="size-6" label="Loading your workspace" />
    </div>
  );
}
