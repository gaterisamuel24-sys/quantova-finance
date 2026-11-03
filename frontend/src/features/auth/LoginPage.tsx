import { useState, type FormEvent } from "react";
import { Link } from "react-router";

import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { Field } from "../../components/ui/Field";
import { Input } from "../../components/ui/Input";
import { PasswordInput } from "../../components/ui/PasswordInput";
import { describeAuthFailure, useAuth } from "./auth-context";
import { AuthLayout } from "./AuthLayout";

export function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      // Success: GuestOnly redirects as soon as the session exists.
    } catch (caught) {
      setError(describeAuthFailure(caught));
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="Sign in to Quantova"
      subtitle="Welcome back. Enter your details to continue."
      footer={
        <>
          New to Quantova?{" "}
          <Link to="/register" className="font-medium text-brand hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <title>Sign in · Quantova Finance</title>
      <form onSubmit={(event) => void handleSubmit(event)} className="grid gap-4">
        {error && <Alert tone="error" title={error} />}
        <Field label="Email">
          {(control) => (
            <Input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              {...control}
            />
          )}
        </Field>
        <Field label="Password">
          {(control) => (
            <PasswordInput
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              {...control}
            />
          )}
        </Field>
        <Button type="submit" loading={submitting} className="mt-2 w-full">
          Sign in
        </Button>
      </form>
    </AuthLayout>
  );
}
