import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { THEME_STORAGE_KEY, useTheme } from "./theme-context";
import { ThemeProvider } from "./ThemeProvider";

function ThemeProbe() {
  const { theme, setTheme } = useTheme();
  return (
    <button type="button" onClick={() => setTheme("dark")}>
      {theme}
    </button>
  );
}

describe("ThemeProvider", () => {
  it("defaults to the system theme, then applies and remembers a choice", () => {
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );
    expect(screen.getByRole("button").textContent).toBe("system");
    expect(document.documentElement.classList.contains("dark")).toBe(false);

    fireEvent.click(screen.getByRole("button"));

    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
  });

  it("restores a saved theme on load", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "light");

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    expect(screen.getByRole("button").textContent).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});
