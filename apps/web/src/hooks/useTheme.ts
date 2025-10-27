import { useEffect, useState } from "react";

export type ThemeMode = "light" | "dark";

export function useTheme() {
  const [theme, setTheme] = useState<ThemeMode>(() => {
    // try localStorage first
    const saved = window.localStorage.getItem("applylens-theme");
    if (saved === "dark" || saved === "light") return saved as ThemeMode;
    // default to dark for now (keep current look by default)
    return "dark";
  });

  useEffect(() => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
      window.localStorage.setItem("applylens-theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      window.localStorage.setItem("applylens-theme", "light");
    }
  }, [theme]);

  return { theme, setTheme };
}
