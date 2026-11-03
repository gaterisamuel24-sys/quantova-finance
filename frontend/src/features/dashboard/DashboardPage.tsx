import { useState } from "react";

import { ThemeToggle } from "../../components/ThemeToggle";
import { Button } from "../../components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader } from "../../components/ui/Card";
import { useAuth } from "../auth/auth-context";

// Temporary signed-in page. Step 3.6 replaces it with the full app shell.
export function DashboardPage() {
  const { user, logout } = useAuth();
  const [signingOut, setSigningOut] = useState(false);

  async function handleSignOut() {
    setSigningOut(true);
    await logout();
  }

  return (
    <>
      <title>Dashboard · Quantova Finance</title>
      <div className="flex justify-end p-4">
        <ThemeToggle />
      </div>
      <main className="mx-auto max-w-xl px-4 py-12">
        <Card>
          <CardHeader>
            <h1 className="text-2xl font-semibold tracking-tight">Welcome, {user?.full_name}</h1>
            <CardDescription>Signed in as {user?.email}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="secondary" loading={signingOut} onClick={() => void handleSignOut()}>
              Sign out
            </Button>
          </CardContent>
        </Card>
      </main>
    </>
  );
}
