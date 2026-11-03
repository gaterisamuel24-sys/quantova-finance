import { useState, type FormEvent } from "react";
import { Link } from "react-router";

import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { Field } from "../../components/ui/Field";
import { Input } from "../../components/ui/Input";
import { PasswordInput } from "../../components/ui/PasswordInput";
import { AuthError, describeAuthFailure, useAuth } from "./auth-context";
import { AuthLayout } from "./AuthLayout";

const PASSWORD_MIN_LENGTH = 12;

export function RegisterPage() {
  const { register } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (password.length < PASSWORD_MIN_LENGTH) {
      setFields({ password: `Use at least ${PASSWORD_MIN_LENGTH} characters.` });
      return;
    }
    setFields({});
    setSubmitting(true);
    try {
      await register({ fullName, email, password });
    } catch (caught) {
      if (caught instanceof AuthError && Object.keys(caught.fieldErrors).length > 0) {
        setFields(caught.fieldErrors);
      } else {
        setError(describeAuthFailure(caught));
      }
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Set up your workspace in under a minute."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-brand hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <title>Create your account · Quantova Finance</title>
      <form onSubmit={(event) => void handleSubmit(event)} className="grid gap-4">
        {error && <Alert tone="error" title={error} />}
        <Field label="Full name" error={fields.full_name}>
          {(control) => (
            <Input
              autoComplete="name"
              required
              maxLength={200}
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              {...control}
            />
          )}
        </Field>
        <Field label="Email" error={fields.email}>
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
        <Field
          label="Password"
          hint={`At least ${PASSWORD_MIN_LENGTH} characters. A memorable passphrase works well.`}
          error={fields.password}
        >
          {(control) => (
            <PasswordInput
              autoComplete="new-password"
              required
              maxLength={128}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              {...control}
            />
          )}
        </Field>
        <Button type="submit" loading={submitting} className="mt-2 w-full">
          Create account
        </Button>
      </form>
    </AuthLayout>
  );
}
