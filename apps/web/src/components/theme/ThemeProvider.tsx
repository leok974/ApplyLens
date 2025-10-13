import * as React from "react";

type Theme = "light" | "dark" | "system";
type Ctx = { theme: Theme; setTheme: (t: Theme) => void; toggle: () => void; };

const ThemeContext = React.createContext<Ctx | null>(null);

function applyTheme(theme: Theme) {
  const root = document.documentElement; // <html>
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const isDark = theme === "dark" || (theme === "system" && prefersDark);
  root.classList.toggle("dark", isDark);
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<Theme>(() => {
    return (localStorage.getItem("theme") as Theme) || "system";
  });

  const setTheme = React.useCallback((t: Theme) => {
    setThemeState(t);
    localStorage.setItem("theme", t);
    applyTheme(t);
  }, []);

  const toggle = React.useCallback(() => {
    setThemeState((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      localStorage.setItem("theme", next);
      applyTheme(next);
      return next;
    });
  }, []);

  React.useEffect(() => {
    applyTheme(theme);
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => theme === "system" && applyTheme("system");
    mq.addEventListener?.("change", onChange);
    return () => mq.removeEventListener?.("change", onChange);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = React.useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
