"use client";

import * as React from "react";

const ThemeContext = React.createContext<{
  theme: "light" | "dark";
  setTheme: (theme: "light" | "dark") => void;
} | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<"light" | "dark">(() => {
    if (typeof window === "undefined") return "light";
    const stored = localStorage.getItem("harborhomes-theme") as "light" | "dark" | null;
    if (stored) return stored;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  const setTheme = React.useCallback((next: "light" | "dark") => {
    setThemeState(next);
    if (typeof window !== "undefined") {
      document.documentElement.classList.toggle("dark", next === "dark");
      localStorage.setItem("harborhomes-theme", next);
    }
  }, []);

  React.useEffect(() => {
    setTheme(theme);
  }, [setTheme, theme]);

  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = React.useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}
