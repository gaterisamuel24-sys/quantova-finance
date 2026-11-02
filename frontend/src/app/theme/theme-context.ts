import { createContext, useContext } from "react";

export type Theme = "light" | "dark" | "system";

export const THEME_STORAGE_KEY = "quantova-theme";

export type ThemeContextValue = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
};

export const ThemeContext = createContext<ThemeContextValue | null>(null);

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (context === null) {
    throw new Error("useTheme must be used inside <ThemeProvider>");
  }
  return context;
}
