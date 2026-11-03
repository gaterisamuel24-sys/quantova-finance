import type { ComponentProps } from "react";

import { buttonClasses, type ButtonSize, type ButtonVariant } from "./button-styles";
import { Spinner } from "./Spinner";

export type ButtonProps = ComponentProps<"button"> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Shows a spinner, disables the button and marks it busy for assistive technology. */
  loading?: boolean;
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  type = "button",
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClasses({ variant, size, className })}
      {...props}
    >
      {loading && <Spinner className="size-4" label={null} />}
      {children}
    </button>
  );
}
