import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Alert } from "./Alert";
import { Button } from "./Button";
import { Field } from "./Field";
import { Input } from "./Input";

describe("Button", () => {
  it("does not submit forms by default and handles clicks", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Save</Button>);

    const button = screen.getByRole("button", { name: "Save" });
    fireEvent.click(button);

    expect(button.getAttribute("type")).toBe("button");
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("is disabled and marked busy while loading", () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Pay invoice
      </Button>,
    );

    const button = screen.getByRole("button", { name: "Pay invoice" });
    fireEvent.click(button);

    expect(button).toHaveProperty("disabled", true);
    expect(button.getAttribute("aria-busy")).toBe("true");
    expect(onClick).not.toHaveBeenCalled();
  });
});

describe("Field", () => {
  it("links the label and hint to the control", () => {
    render(
      <Field label="Email" hint="We never share your email.">
        {(control) => <Input type="email" {...control} />}
      </Field>,
    );

    const input = screen.getByLabelText("Email");
    const description = document.getElementById(input.getAttribute("aria-describedby") ?? "");

    expect(description?.textContent).toBe("We never share your email.");
    expect(input.getAttribute("aria-invalid")).toBeNull();
  });

  it("marks the control invalid and describes it with the error", () => {
    render(
      <Field label="Email" hint="We never share your email." error="Enter a valid email address.">
        {(control) => <Input type="email" {...control} />}
      </Field>,
    );

    const input = screen.getByLabelText("Email");
    const description = document.getElementById(input.getAttribute("aria-describedby") ?? "");

    expect(input.getAttribute("aria-invalid")).toBe("true");
    expect(description?.textContent).toBe("Enter a valid email address.");
  });
});

describe("Alert", () => {
  it("interrupts for errors and announces other tones politely", () => {
    render(
      <>
        <Alert tone="error" title="Payment failed" />
        <Alert tone="success" title="Changes saved" />
      </>,
    );

    expect(screen.getByRole("alert").textContent).toContain("Payment failed");
    expect(screen.getByRole("status").textContent).toContain("Changes saved");
  });
});
