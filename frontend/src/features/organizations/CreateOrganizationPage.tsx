import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";

import { Logo } from "../../components/brand/Logo";
import { ThemeToggle } from "../../components/ThemeToggle";
import { Alert } from "../../components/ui/Alert";
import { Button } from "../../components/ui/Button";
import { buttonClasses } from "../../components/ui/button-styles";
import { Card, CardContent } from "../../components/ui/Card";
import { Field } from "../../components/ui/Field";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { ApiRequestError } from "../../lib/api/errors";
import { UserMenu } from "../app-shell/UserMenu";
import { useCreateOrganization, useOrganizations } from "./api";

const CURRENCIES = [
  ["USD", "US dollar"],
  ["EUR", "Euro"],
  ["GBP", "British pound"],
  ["KES", "Kenyan shilling"],
  ["NGN", "Nigerian naira"],
  ["ZAR", "South African rand"],
  ["UGX", "Ugandan shilling"],
  ["TZS", "Tanzanian shilling"],
  ["INR", "Indian rupee"],
  ["CAD", "Canadian dollar"],
  ["AUD", "Australian dollar"],
] as const;

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export function CreateOrganizationPage() {
  const { data: organizations } = useOrganizations();
  const createOrganization = useCreateOrganization();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [fiscalMonth, setFiscalMonth] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});

  const isFirst = organizations?.length === 0;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setFields({});
    try {
      const organization = await createOrganization.mutateAsync({
        name,
        base_currency: currency,
        fiscal_year_start_month: fiscalMonth,
      });
      navigate(`/app/${organization.id}`);
    } catch (caught) {
      if (caught instanceof ApiRequestError && Object.keys(caught.fieldErrors).length > 0) {
        setFields(caught.fieldErrors);
      } else {
        setError(caught instanceof Error ? caught.message : "Could not create the organization.");
      }
    }
  }

  return (
    <div className="min-h-screen">
      <title>Create an organization · Quantova Finance</title>
      <header className="flex h-16 items-center justify-between border-b px-4 sm:px-6">
        <Link to="/app" aria-label="Quantova Finance">
          <Logo />
        </Link>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <UserMenu />
        </div>
      </header>

      <main className="mx-auto max-w-lg px-4 py-12">
        <h1 className="text-2xl font-semibold tracking-tight">
          {isFirst ? "Create your first organization" : "Create an organization"}
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          An organization is a workspace for one business or client. Its financial data is visible
          only to its members.
        </p>

        <Card className="mt-8">
          <CardContent>
            <form onSubmit={(event) => void handleSubmit(event)} className="grid gap-5">
              {error && <Alert tone="error" title={error} />}
              <Field label="Organization name" error={fields.name}>
                {(control) => (
                  <Input
                    required
                    maxLength={200}
                    autoComplete="organization"
                    placeholder="Acme Ltd"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    {...control}
                  />
                )}
              </Field>
              <Field
                label="Base currency"
                hint="Reports and dashboards use this currency."
                error={fields.base_currency}
              >
                {(control) => (
                  <Select
                    value={currency}
                    onChange={(event) => setCurrency(event.target.value)}
                    {...control}
                  >
                    {CURRENCIES.map(([code, label]) => (
                      <option key={code} value={code}>
                        {code} · {label}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
              <Field
                label="Fiscal year starts in"
                hint="Used for yearly and quarterly reports."
                error={fields.fiscal_year_start_month}
              >
                {(control) => (
                  <Select
                    value={fiscalMonth}
                    onChange={(event) => setFiscalMonth(Number(event.target.value))}
                    {...control}
                  >
                    {MONTHS.map((month, index) => (
                      <option key={month} value={index + 1}>
                        {month}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
              <div className="mt-2 flex justify-end gap-3">
                {!isFirst && (
                  <Link to="/app" className={buttonClasses({ variant: "ghost" })}>
                    Cancel
                  </Link>
                )}
                <Button type="submit" loading={createOrganization.isPending}>
                  Create organization
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
