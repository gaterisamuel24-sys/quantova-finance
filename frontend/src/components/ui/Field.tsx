import { useId, type ReactNode } from "react";

import { cn } from "../../lib/cn";
import { Label } from "./Label";

type ControlProps = {
  id: string;
  "aria-describedby"?: string;
  "aria-invalid"?: true;
};

type FieldProps = {
  label: string;
  hint?: string;
  error?: string;
  className?: string;
  /** Render the control, spreading the provided props onto it: {(control) => <Input {...control} />} */
  children: (control: ControlProps) => ReactNode;
};

/** A labelled form control with optional hint and error, wired up for assistive technology. */
export function Field({ label, hint, error, className, children }: FieldProps) {
  const id = useId();
  const messageId = `${id}-message`;
  const message = error ?? hint;

  return (
    <div className={cn("grid gap-1.5", className)}>
      <Label htmlFor={id}>{label}</Label>
      {children({
        id,
        "aria-describedby": message ? messageId : undefined,
        "aria-invalid": error ? true : undefined,
      })}
      {message && (
        <p
          id={messageId}
          className={cn("text-xs", error ? "font-medium text-negative" : "text-muted-foreground")}
        >
          {message}
        </p>
      )}
    </div>
  );
}
